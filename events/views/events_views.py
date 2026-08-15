# events_views.py - VISTA COMPLETA REORGANIZADA Y OPTIMIZADA
# ============================================================================
# IMPORTACIONES
# ============================================================================

# Django Imports
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string

User = get_user_model()
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import Q, Count
from django.http import HttpResponse

# Models
from ..models import Event, EventState, EventAttendee, Status, Project, Task

# Forms
from ..forms import CreateNewEvent

# Utilidades centralizadas
from ..utils import (
    # Status
    statuses_get,
    get_default_status,
    
    # Permisos
    is_superuser,
    has_event_permission,
    can_edit_event,
    get_editable_events,
    check_edit_permissions,
    
    # Managers
    get_managers_for_user,
    
    # Chart/Metrics
    get_card_data
)

# Python standard libraries
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


# ============================================================================
# VISTAS PRINCIPALES DE EVENTOS
# ============================================================================

@login_required
def events(request):
    logger.info(f"Events view started by user: {request.user.username}")
    
    try:
        today = timezone.now().date()
        title = "Events Origin"

        # Inicializar filtros de sesión
        _initialize_session_filters(request, today)
        
        # Obtener managers y datos
        managers = get_managers_for_user(request.user)
        all_events, active_events = managers['event_manager'].get_all_events()
        event_statuses = Status.objects.all().order_by('status_name')

        # Aplicar filtros
        if request.method == 'POST':
            filtered_events = _apply_filters_from_request(request, all_events)
        else:
            filtered_events = _apply_stored_filters(request, all_events)

        # Fechas para filtros rápidos
        start_of_month = today.replace(day=1)
        start_of_year = today.replace(month=1, day=1)

        # Preparar contexto
        context = {
            'title': title,
            'events_updated_today': _count_events_updated_today(filtered_events, today),
            'count_events': len(filtered_events),
            'events': filtered_events,
            'event_statuses': event_statuses,
            'events_states': EventState.objects.all().order_by('-start_time')[:10],
            'metrics': get_card_data(request.user, days=30),
            'today': today,
            'start_of_month': start_of_month,
            'start_of_year': start_of_year,
            'hosts': User.objects.filter(
                Q(pk__in=Event.objects.values_list('host', flat=True).distinct()) |
                Q(pk__in=Event.objects.values_list('assigned_to', flat=True).distinct())
            ).distinct(),
        }
        
        return render(request, 'events/events.html', context)
    except Exception as e:
        logger.critical(f"Unexpected error in events view: {str(e)}", exc_info=True)
        messages.error(request, f'Error al procesar eventos: {e}')
        return redirect('home')


@login_required
def events_table(request):
    if request.method == 'GET':
        managers = get_managers_for_user(request.user)
        all_events, active_events = managers['event_manager'].get_all_events()
        search = request.GET.get('search', '').strip()
        status = request.GET.get('status')
        host = request.GET.get('host')
        date_str = request.GET.get('date')
        sort_key = request.GET.get('sort')
        sort_dir = request.GET.get('dir', 'asc')

        filtered_events = _apply_filters_to_events(
            all_events,
            completed=False,
            status=status if status else None,
            date_str=date_str if date_str else None
        )

        if search:
            filtered_events = [
                e for e in filtered_events
                if search.lower() in e['event'].title.lower()
                or search.lower() in e['event'].host.username.lower()
            ]

        if host:
            filtered_events = [e for e in filtered_events if str(e['event'].host_id) == host]

        filtered_events = list(filtered_events)
        if sort_key in {'id', 'title', 'status', 'host', 'date'}:
            filtered_events.sort(key=lambda e: (
                e['event'].id if sort_key == 'id' else
                e['event'].title.lower() if sort_key == 'title' else
                e['event'].event_status.status_name.lower() if sort_key == 'status' else
                e['event'].host.username.lower() if sort_key == 'host' else
                e['event'].created_at.isoformat()
            ))
            if sort_dir == 'desc':
                filtered_events.reverse()

        html = render_to_string('events/includes/events_table_rows.html', {
            'events': filtered_events,
        }, request=request)
        return HttpResponse(html)
    return HttpResponse(status=405)


@login_required
def event_detail(request, event_id):
    """
    Vista detallada de un evento.
    """
    try:
        event = get_object_or_404(
            Event.objects.select_related('event_status', 'host', 'assigned_to')
            .prefetch_related('attendees'),
            id=event_id
        )
        
        if not has_event_permission(request.user, event, 'view'):
            messages.error(request, 'No tienes permisos para ver este evento.')
            return redirect('events:events')
        
        return render(request, 'events/event_detail.html', _get_event_detail_context(event))
        
    except Exception as e:
        logger.error(f"Error in event_detail {event_id}: {e}", exc_info=True)
        messages.error(request, f'Error al cargar el evento: {e}')
        return redirect('events:events')


@login_required
def event_panel(request, event_id=None):
    """
    Panel de eventos - Vista general o detallada.
    """
    title = "Event Panel"
    
    try:
        event_statuses, project_statuses, task_statuses = statuses_get()
        managers = get_managers_for_user(request.user)
        
        if event_id:
            return _render_event_detail_panel(
                request, event_id, title, managers,
                event_statuses, project_statuses, task_statuses
            )
        
        return _render_event_general_panel(
            request, title, managers['event_manager'],
            event_statuses, project_statuses, task_statuses
        )
        
    except Exception as e:
        logger.error(f"Error in event_panel: {e}", exc_info=True)
        messages.error(request, f'Error al cargar el panel: {e}')
        return redirect('events:events')


# ============================================================================
# VISTAS DE CREACIÓN Y EDICIÓN
# ============================================================================

@login_required
def event_create(request):
    """
    Crear un nuevo evento.
    """
    title = "Create New Event"
    
    try:
        if request.method == 'GET':
            return _render_event_create_form(request, title)
        return _process_event_create_form(request, title)
        
    except Exception as e:
        messages.error(request, f'Error inesperado: {e}')
        return redirect('home')


@login_required
def event_edit(request, event_id=None):
    """
    Editar evento existente o listar eventos editables.
    """
    try:
        if event_id:
            return _handle_edit_existing_event(request, event_id)
        return _handle_list_events_for_edit(request)
            
    except Event.DoesNotExist:
        messages.error(request, 'El evento no existe.')
        return redirect('events:event_panel')
    except PermissionDenied as e:
        messages.error(request, str(e))
        return redirect('events:event_panel')
    except Exception as e:
        logger.error(f"Error in event_edit: {e}", exc_info=True)
        messages.error(request, 'Error inesperado.')
        return redirect('home')


# ============================================================================
# VISTAS DE ASIGNACIÓN Y GESTIÓN
# ============================================================================

@login_required
def event_assign(request, event_id=None):
    """
    Asignar proyectos/tareas a un evento o listar eventos asignables.
    """
    title = "Event Assign"
    
    try:
        event_statuses, project_statuses, task_statuses = statuses_get()
        
        if event_id:
            return _assign_to_specific_event(
                request, event_id, title,
                event_statuses, project_statuses, task_statuses
            )
        return _list_events_for_assign(request, title)
        
    except Exception as e:
        messages.error(request, f'Error: {e}')
        return redirect('home')


@login_required
def event_status_change(request, event_id):
    """
    Cambiar estado de un evento.
    """
    if request.method != 'POST':
        return HttpResponse("Método no permitido", status=405)
    
    try:
        event = get_object_or_404(Event, pk=event_id)
        new_status = get_object_or_404(Status, pk=request.POST.get('new_status_id'))
        
        if not can_edit_event(request.user, event):
            return HttpResponse("Sin permisos", status=403)
        
        _update_event_status(event, request.user, new_status)
        messages.success(request, 'Estado actualizado exitosamente.')
        return redirect('events:events')
        
    except Exception as e:
        logger.error(f"Error changing event status: {e}", exc_info=True)
        return HttpResponse(f"Error: {e}", status=500)


@login_required
def assign_attendee_to_event(request, event_id, user_id):
    """
    Asignar asistente a evento.
    """
    try:
        event = get_object_or_404(Event, pk=event_id)
        
        # ========== MEJORA DE SEGURIDAD ==========
        if not can_edit_event(request.user, event):
            messages.error(request, 'No tienes permiso para modificar este evento.')
            return redirect('events:event_detail', event_id=event_id)
        # ==========================================
        
        user = get_object_or_404(User, pk=user_id, is_active=True)
        _, created = EventAttendee.objects.get_or_create(user=user, event=event)

        if created:
            messages.success(request, 'Asistente asignado con éxito.')
        else:
            messages.info(request, 'El asistente ya estaba asignado.')

        return redirect('events:event_detail', event_id=event_id)
        
    except Exception as e:
        messages.error(request, f'Error al asignar asistente: {e}')
        return redirect('home')


# ============================================================================
# VISTAS DE ELIMINACIÓN Y ACCIONES MASIVAS
# ============================================================================

@login_required
def event_delete(request, event_id):
    """
    Eliminar un evento (solo superusuarios).
    """
    if request.method != 'POST':
        messages.error(request, 'Método no permitido.')
        return redirect('events:event_panel')
    
    event = get_object_or_404(Event, pk=event_id)

    if not is_superuser(request.user):
        messages.error(request, 'No tienes permiso para eliminar eventos.')
        return redirect('events:event_panel')

    event.delete()
    messages.success(request, 'Evento eliminado exitosamente.')
    return redirect('events:event_panel')


@login_required
def event_bulk_action(request):
    """
    Acciones masivas para eventos.
    """
    if request.method != 'POST':
        messages.error(request, 'Método no permitido.')
        return redirect('events:event_panel')
    
    action = request.POST.get('action')
    selected_events = request.POST.getlist('selected_items')

    if not selected_events:
        messages.error(request, 'No se seleccionaron eventos.')
        return redirect('events:event_panel')

    # ========== MEJORA DE SEGURIDAD ==========
    events = get_editable_events(request.user).filter(id__in=selected_events)
    # ==========================================
    
    try:
        if action == 'delete':
            if not is_superuser(request.user):
                messages.error(request, 'Sin permiso para eliminar.')
                return redirect('events:event_panel')
            count = events.count()
            events.delete()
            messages.success(request, f'{count} evento(s) eliminado(s).')
        
        elif action == 'activate':
            status = Status.objects.get(status_name='In Progress')
            count = events.update(event_status=status)
            messages.success(request, f'{count} evento(s) activado(s).')
        
        elif action == 'complete':
            status = Status.objects.get(status_name='Completed')
            count = events.update(event_status=status)
            messages.success(request, f'{count} evento(s) completado(s).')
            
    except Status.DoesNotExist:
        messages.error(request, 'Estado no encontrado.')
    except Exception as e:
        messages.error(request, f'Error en acción masiva: {e}')
    
    return redirect('events:event_panel')


# ============================================================================
# VISTAS DE EXPORTACIÓN E HISTORIAL
# ============================================================================

@login_required
def event_export(request):
    """
    Exportar eventos a CSV.
    """
    import csv
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="events_export.csv"'

    writer = csv.writer(response)
    writer.writerow(['ID', 'Título', 'Descripción', 'Estado', 'Lugar', 'Host', 'Creado'])

    # ========== MEJORA DE SEGURIDAD ==========
    if is_superuser(request.user):
        events = Event.objects.all()
    else:
        events = Event.objects.filter(
            Q(host=request.user) |
            Q(assigned_to=request.user) |
            Q(attendees=request.user)
        ).distinct()
    events = events.select_related('event_status', 'host')
    # ==========================================
    
    for event in events:
        writer.writerow([
            event.id,
            event.title,
            event.description or '',
            event.event_status.status_name if event.event_status else '',
            event.venue or '',
            event.host.username if event.host else '',
            event.created_at.strftime('%Y-%m-%d %H:%M:%S')
        ])

    return response


@login_required
def event_history(request, event_id=None):
    """
    Historial de estados de eventos.
    """
    title = 'Event History'
    
    if event_id:
        event = get_object_or_404(Event, pk=event_id)
        # ========== MEJORA DE SEGURIDAD ==========
        if not has_event_permission(request.user, event, 'view'):
            messages.error(request, 'No tienes permiso para ver este evento.')
            return redirect('events:events')
        # ==========================================
        productive_status = get_default_status('event', 'In Progress')
        events_history = EventState.objects.filter(
            Q(event_id=event_id, event_status=productive_status)
        ).order_by('-start_time')
    else:
        # ========== MEJORA DE RENDIMIENTO Y SEGURIDAD ==========
        thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
        events_history = EventState.objects.filter(
            start_time__gte=thirty_days_ago
        ).order_by('-start_time')
        # =======================================================
    
    # ========== PAGINACIÓN ==========
    paginator = Paginator(events_history, 50)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    # ================================
    
    return render(request, 'events/event_history.html', {
        'title': title,
        'events_history': page_obj.object_list,
        'page_obj': page_obj,
    })


# ============================================================================
# FUNCIONES AUXILIARES - FILTRADO
# ============================================================================

def _initialize_session_filters(request, today):
    """Inicializar filtros de sesión."""
    if request.session.get('first_session', True):
        request.session.setdefault('filtered_completed', False)
        request.session.setdefault('filtered_status', None)
        request.session.setdefault('filtered_date', None)
        request.session['first_session'] = False


def _apply_filters_from_request(request, all_events):
    """Aplicar filtros desde request POST."""
    completed = request.POST.get('completed', 'False').lower() == 'true'
    status = int(request.POST.get('status')) if request.POST.get('status') else None
    date_str = request.POST.get('date')
    
    request.session.update({
        'filtered_completed': completed,
        'filtered_status': status,
        'filtered_date': date_str
    })
    
    return _apply_filters_to_events(all_events, completed, status, date_str)


def _apply_stored_filters(request, all_events):
    """Aplicar filtros almacenados en sesión."""
    return _apply_filters_to_events(
        all_events,
        request.session.get('filtered_completed'),
        request.session.get('filtered_status'),
        request.session.get('filtered_date')
    )


def _apply_filters_to_events(events, completed, status, date_str):
    """Aplicar filtros a la lista de eventos."""
    filtered_events = events
    
    try:
        if completed:
            status_completed = Status.objects.get(status_name='Completed')
            filtered_events = [
                e for e in filtered_events 
                if e['event'].event_status_id != status_completed.id
            ]
        
        if status:
            status_map = {
                'active': 'In Progress',
                'completed': 'Completed',
                'planned': 'Created',
            }
            status_name = status_map.get(str(status))
            if status_name:
                status_obj = Status.objects.get(status_name=status_name)
                filtered_events = [
                    e for e in filtered_events 
                    if e['event'].event_status_id == status_obj.id
                ]
        
        if date_str:
            filter_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            filtered_events = [
                e for e in filtered_events 
                if e['event'].updated_at.date() == filter_date
            ]
            
    except (Status.DoesNotExist, ValueError) as e:
        logger.error(f"Filtering error: {e}")
        
    return filtered_events


def _count_events_updated_today(events, today):
    """Contar eventos actualizados hoy."""
    return len([
        e for e in events 
        if e['event'].updated_at.date() == today
    ])


# ============================================================================
# FUNCIONES AUXILIARES - CONTEXTO DE EVENTOS
# ============================================================================

def _get_event_detail_context(event):
    """Contexto para vista detallada de evento."""
    projects = Project.objects.filter(event=event).select_related(
        'project_status', 'assigned_to'
    ).prefetch_related('attendees').order_by('-created_at')
    
    tasks = Task.objects.filter(event=event).select_related(
        'task_status', 'assigned_to', 'project'
    ).order_by('-created_at')
    
    total_tasks = tasks.count()
    completed_tasks = tasks.filter(task_status__status_name='Completed').count()
    
    try:
        completed_status = Status.objects.get(status_name='Completed')
        completed_status_id = completed_status.id
    except Status.DoesNotExist:
        completed_status_id = None
    
    return {
        'title': f'Evento: {event.title}',
        'event': event,
        'total_projects': projects.count(),
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'in_progress_tasks': tasks.filter(task_status__status_name='In Progress').count(),
        'progress_percentage': (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0,
        'projects': projects,
        'tasks': tasks,
        'event_states': EventState.objects.filter(event=event).order_by('-start_time')[:20],
        'attendees': event.attendees.all(),
        'task_status_distribution': tasks.values('task_status__status_name')
            .annotate(count=Count('id')).order_by('task_status__status_name'),
        'upcoming_states': EventState.objects.filter(
            event=event, end_time__gte=timezone.now()
        ).order_by('start_time')[:5],
        'completed_status_id': completed_status_id,
        'is_active': event.event_status.status_name == 'In Progress',
        'is_completed': event.event_status.status_name == 'Completed',
        'is_planned': event.event_status.status_name == 'Planned',
    }


def _render_event_detail_panel(request, event_id, title, managers,
                             event_statuses, project_statuses, task_statuses):
    """Renderizar panel detallado de evento."""
    event_data = managers['event_manager'].get_event_by_id(event_id)
    
    if not event_data:
        messages.error(request, f'Evento ID {event_id} no encontrado.')
        return redirect('events:events')
    
    context = {
        'page': 'event_detail',
        'title': f'{title} - {event_data.get("title", "Detalle")}',
        'event_data': event_data,
        'event_statuses': event_statuses,
        'project_statuses': project_statuses,
        'task_statuses': task_statuses,
    }
    
    # Proyectos relacionados
    if event_data.get('projects'):
        try:
            context['projects_data'] = [
                managers['project_manager'].get_project_data(p.id)
                for p in event_data['projects']
            ]
        except Exception as e:
            logger.warning(f"Error loading projects: {e}")
            context['projects_data'] = []
            messages.warning(request, 'Algunos proyectos no se pudieron cargar.')
    else:
        context['projects_data'] = []
        messages.info(request, 'Este evento no tiene proyectos.')
    
    # Tareas relacionadas
    if event_data.get('tasks'):
        try:
            context['tasks_data'] = [
                managers['task_manager'].get_task_data(t)
                for t in event_data['tasks']
            ]
        except Exception as e:
            logger.warning(f"Error loading tasks: {e}")
            context['tasks_data'] = []
            messages.warning(request, 'Algunas tareas no se pudieron cargar.')
    else:
        context['tasks_data'] = []
        messages.info(request, 'Este evento no tiene tareas.')
    
    return render(request, "events/event_panel.html", context)


def _render_event_general_panel(request, title, event_manager,
                              event_statuses, project_statuses, task_statuses):
    """Renderizar panel general de eventos."""
    events, active_events = event_manager.get_all_events()
    stats = _calculate_event_statistics(events)
    
    return render(request, 'events/event_panel.html', {
        'page': 'event_panel',
        'title': title,
        'events': events,
        'event_details': _prepare_event_details_dict(events),
        'event_statuses': event_statuses,
        'project_statuses': project_statuses,
        'task_statuses': task_statuses,
        'events_states': EventState.objects.select_related('event', 'status')
            .order_by('-start_time')[:10],
        'active_events': active_events,
        'total_events': stats['total'],
        'in_progress_count': stats['in_progress'],
        'completed_count': stats['completed'],
        'created_count': stats['created'],
        'other_count': stats.get('other', 0),
    })


def _calculate_event_statistics(events):
    """Calcular estadísticas de eventos."""
    if not events:
        return {'total': 0, 'in_progress': 0, 'completed': 0, 'created': 0, 'other': 0}
    
    counters = {'In Progress': 0, 'Completed': 0, 'Created': 0, 'total': len(events)}
    
    for event_data in events:
        event_obj = event_data.get('event')
        if event_obj and event_obj.event_status:
            status_name = event_obj.event_status.status_name
            if status_name in counters:
                counters[status_name] += 1
            else:
                counters['other'] = counters.get('other', 0) + 1
    
    return {
        'total': counters['total'],
        'in_progress': counters.get('In Progress', 0),
        'completed': counters.get('Completed', 0),
        'created': counters.get('Created', 0),
        'other': counters.get('other', 0)
    }


def _prepare_event_details_dict(events):
    """Preparar diccionario de detalles por evento."""
    details = {}
    for event_data in events:
        event = event_data.get('event')
        if event and hasattr(event, 'id'):
            details[event.id] = {
                'projects': event_data.get('projects', []),
                'tasks': event_data.get('tasks', []),
                'title': event.title,
                'status': event.event_status.status_name if event.event_status else 'Sin Estado'
            }
    return details


# ============================================================================
# FUNCIONES AUXILIARES - CREACIÓN DE EVENTOS
# ============================================================================

def _render_event_create_form(request, title):
    """Renderizar formulario de creación."""
    try:
        default_status = Status.objects.get(status_name='Created').id
    except Status.DoesNotExist:
        messages.error(request, 'El estado "Creado" no existe.')
        return redirect('home')

    form = CreateNewEvent(initial={
        'assigned_to': request.user.id,
        'host': request.user.id,
        'event_status': default_status
    })
    
    return render(request, 'events/event_create.html', {
        'form': form,
        'title': title,
    })


def _process_event_create_form(request, title):
    """Procesar formulario de creación."""
    form = CreateNewEvent(request.POST)
    
    if not form.is_valid():
        _display_form_errors(request, form)
        return render(request, 'events/event_create.html', {'form': form, 'title': title})
    
    try:
        # ========== ELIMINADA PUERTA TRASERA 'inbound' ==========
        if is_superuser(request.user):
            initial_status_id = request.POST.get('event_status')
        else:
            initial_status_id = Status.objects.get(status_name='Created').id
        # ========================================================
        
        initial_status = Status.objects.get(id=initial_status_id)
        
        # Crear evento
        new_event = form.save(commit=False)
        new_event.event_status = initial_status
        new_event.host = request.user
        
        if not is_superuser(request.user):
            new_event.assigned_to = request.user
        
        new_event.save()
        
        # Asignar asistentes
        for attendee in form.cleaned_data.get('attendees', []):
            EventAttendee.objects.create(user=attendee, event=new_event)
        
        messages.success(request, 'Evento creado con éxito.')
        return redirect('events:events')
        
    except (Status.DoesNotExist, IntegrityError) as e:
        messages.error(request, f'Error al crear evento: {e}')
        return render(request, 'events/event_create.html', {'form': form, 'title': title})


# ============================================================================
# FUNCIONES AUXILIARES - ASIGNACIÓN DE EVENTOS
# ============================================================================

def _assign_to_specific_event(request, event_id, title,
                            event_statuses, project_statuses, task_statuses):
    """Asignar recursos a evento específico."""
    managers = get_managers_for_user(request.user)
    event_data = managers['event_manager'].get_event_by_id(event_id)
    
    if not event_data:
        messages.error(request, 'El evento no existe.')
        return redirect('home')
    
    if request.method == 'POST':
        return _process_assign_form(request, event_id, managers, event_data)
    
    # GET - mostrar formulario
    available_projects = managers['project_manager'].user_projects.exclude(
        id__in=[p.id for p in event_data.get('projects', [])]
    )
    available_tasks = managers['task_manager'].user_tasks.exclude(
        id__in=[t.id for t in event_data.get('tasks', [])]
    )
    
    return render(request, "events/event_assign.html", {
        'title': f'{title} (Evento ID: {event_id})',
        'event': event_data,
        'available_projects': available_projects,
        'available_tasks': available_tasks,
        'event_statuses': event_statuses,
        'project_statuses': project_statuses,
        'task_statuses': task_statuses,
    })


def _process_assign_form(request, event_id, managers, event_data):
    """Procesar formulario de asignación."""
    task_id = request.POST.get('assign_task_id')
    project_id = request.POST.get('assign_project_id')
    
    # ========== MEJORA DE SEGURIDAD ==========
    event_obj = event_data.get('event')
    if not event_obj or not can_edit_event(request.user, event_obj):
        messages.error(request, 'No tienes permiso para modificar este evento.')
        return redirect('event_assign', event_id=event_id)
    # ==========================================
    
    if task_id:
        task = get_object_or_404(Task, id=task_id)
        # ========== MEJORA DE SEGURIDAD ==========
        if task not in managers['task_manager'].user_tasks.all():
            messages.error(request, 'No tienes permiso para asignar esta tarea.')
            return redirect('event_assign', event_id=event_id)
        # ==========================================
        task.event_id = event_id
        task.save()
        messages.success(request, f'Tarea {task.id} asignada al evento.')
        
    elif project_id:
        project = get_object_or_404(Project, id=project_id)
        # ========== MEJORA DE SEGURIDAD ==========
        if project not in managers['project_manager'].user_projects.all():
            messages.error(request, 'No tienes permiso para asignar este proyecto.')
            return redirect('event_assign', event_id=event_id)
        # ==========================================
        project.event_id = event_id
        project.save()
        messages.success(request, f'Proyecto {project.id} asignado al evento.')
        
    else:
        messages.error(request, 'No se proporcionó ID válido.')
        return redirect('event_assign', event_id=event_id)
    
    return redirect('event_assign', event_id=event_id)


def _list_events_for_assign(request, title):
    """Listar eventos disponibles para asignación."""
    managers = get_managers_for_user(request.user)
    events, _ = managers['event_manager'].get_all_events()
    
    return render(request, "events/event_assign.html", {
        'title': f'{title} (Seleccionar Evento)',
        'events': events,
    })


def _update_event_status(event, user, new_status):
    """Actualizar estado de evento y registrar cambio."""
    old_status = event.event_status
    
    event.record_edit(
        editor=user,
        field_name='event_status',
        old_value=str(old_status),
        new_value=str(new_status)
    )
    
    event.event_status = new_status
    event.save()
    
    logger.info(f"Event {event.id} status changed: {old_status} -> {new_status}")


# ============================================================================
# FUNCIONES AUXILIARES - EDICIÓN DE EVENTOS
# ============================================================================

def _handle_edit_existing_event(request, event_id):
    """Editar evento existente."""
    event = get_object_or_404(
        Event.objects.select_related('event_status', 'host', 'assigned_to'),
        pk=event_id
    )
    
    check_edit_permissions(request.user, event)
    
    if request.method == 'POST':
        return _process_edit_form(request, event)
    return _render_edit_form(request, event)


def _handle_list_events_for_edit(request):
    """Listar eventos editables."""
    events = get_editable_events(request.user)
    
    return render(request, 'events/event_list.html', {
        'title': "Event Edit - Select Event",
        'events': events,
        'total_events': events.count(),
        'user_can_create': request.user.has_perm('events.add_event'),
    })


def _process_edit_form(request, event):
    """Procesar formulario de edición."""
    form = CreateNewEvent(request.POST, instance=event)
    
    if not form.is_valid():
        _display_form_errors(request, form)
        return _render_edit_form(request, event, form)
    
    try:
        _record_changes(request.user, event, form)
        updated_event = form.save()
        
        logger.info(f"Event {event.id} updated by {request.user.id}")
        messages.success(request, 'Evento actualizado exitosamente.')
        
        return _handle_redirect_after_save(request, updated_event)
        
    except Exception as e:
        logger.error(f"Error saving event {event.id}: {e}", exc_info=True)
        messages.error(request, f'Error al guardar: {e}')
        return _render_edit_form(request, event, form)


def _render_edit_form(request, event, form=None):
    """Renderizar formulario de edición."""
    if form is None:
        form = CreateNewEvent(instance=event)
    
    return render(request, 'events/event_edit.html', {
        'title': f'Edit Event: {event.title}',
        'event': event,
        'form': form,
        'attendees_count': event.attendees.count(),
        'can_delete': is_superuser(request.user) and not _has_related_objects(event),
        'can_change_status': is_superuser(request.user) or 
                           event.host == request.user or 
                           event.assigned_to == request.user,
        'status_options': _get_status_options(request.user, event),
        'time_since_update': timezone.now() - event.updated_at,
        'instructions': True,
    })


def _display_form_errors(request, form):
    """Mostrar errores del formulario."""
    for field, errors in form.errors.items():
        field_name = form.fields[field].label if field in form.fields else field
        for error in errors:
            messages.error(request, f'{field_name}: {error}')


def _record_changes(user, event, form):
    """Registrar cambios del formulario."""
    for field in form.changed_data:
        try:
            old_value = getattr(event, field)
            new_value = form.cleaned_data.get(field)
            
            event.record_edit(
                editor=user,
                field_name=field,
                old_value=str(old_value) if old_value else '',
                new_value=str(new_value) if new_value else '',
            )
            
        except Exception as e:
            logger.warning(f"Error recording change for '{field}': {e}")


def _handle_redirect_after_save(request, event):
    """Redirigir después de guardar."""
    next_url = request.POST.get('next')
    
    if next_url and next_url.startswith('/'):
        return redirect(next_url)
    
    if 'save_and_view' in request.POST:
        return redirect('events:event_detail', event_id=event.id)
    if 'save_and_continue' in request.POST:
        return redirect('events:event_edit', event_id=event.id)
    if 'save_and_new' in request.POST:
        return redirect('events:event_create')
    
    return redirect('events:event_panel')


def _get_status_options(user, event):
    """Obtener opciones de estado disponibles."""
    from ..models import Status
    
    if is_superuser(user):
        return Status.objects.all().order_by('status_name')
    
    return Status.objects.filter(
        Q(id=event.event_status.id) | Q(active=True)
    ).order_by('status_name')


def _has_related_objects(event):
    """Verificar si el evento tiene objetos relacionados."""
    from ..models import Project, Task
    
    return (Project.objects.filter(event=event).exists() or 
            Task.objects.filter(event=event).exists())
            
# Añade esta función a tu vista 
def update_event(request):
    if request.method == 'POST':
        # Obtén el ID del evento y si está seleccionado o no
        evento_id = request.POST.get('evento')
        selected = request.POST.get('selected') == 'true'

        # Encuentra el evento en la base de datos
        evento = Event.objects.get(id=evento_id)

        # Actualiza el estado del evento
        evento.estado = 'Completed' if selected else 'No Completed'
        evento.save()

        return JsonResponse({'success': True})

    return JsonResponse({'success': False})

# Otros
def panel(request):
    events = Event.objects.all().order_by('-created_at')
    #events = events.filter(event_status_id = 2)
    return render(request, 'panel/panel.html', {'events': events})    
