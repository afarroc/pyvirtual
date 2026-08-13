# events/dashboard_views.py
# ============================================================================
# VISTAS DE DASHBOARDS UNIFICADOS Y PANELES PRINCIPALES
# ============================================================================

import json
import logging
from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model

User = get_user_model()
from django.contrib.contenttypes.models import ContentType
from django.contrib.admin.models import LogEntry
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from ..models import (
    Task, Project, Event, InboxItem, Reminder, 
    InboxItemHistory, SystemEvent
)
from ..services.dashboard_service import RootDashboardService
from ..utils import check_root_access, get_responsive_grid_classes, log_dashboard_access

logger = logging.getLogger(__name__)


# ============================================================================
# DASHBOARD UNIFICADO DE PRODUCTIVIDAD
# ============================================================================

@login_required
def unified_dashboard(request):
    """
    Dashboard unificado que integra todas las herramientas de productividad
    """
    # Obtener datos del usuario
    user = request.user

    # Estadísticas generales
    today = timezone.now().date()
    this_week = today - timedelta(days=7)

    # Tareas del usuario
    user_tasks = Task.objects.filter(
        Q(host=user) | Q(assigned_to=user)
    ).select_related('task_status', 'project', 'event')

    # Proyectos del usuario
    user_projects = Project.objects.filter(
        Q(host=user) | Q(assigned_to=user) | Q(attendees=user)
    ).distinct().select_related('project_status', 'event')

    # Eventos del usuario
    user_events = Event.objects.filter(
        Q(host=user) | Q(assigned_to=user) | Q(attendees=user)
    ).distinct().select_related('event_status')

    # Estadísticas de tareas
    task_stats = {
        'total': user_tasks.count(),
        'completed': user_tasks.filter(task_status__status_name='Completed').count(),
        'in_progress': user_tasks.filter(task_status__status_name='In Progress').count(),
        'pending': user_tasks.filter(task_status__status_name='To Do').count(),
        'overdue': user_tasks.filter(
            Q(updated_at__lt=timezone.now() - timedelta(days=3)) &
            ~Q(task_status__status_name='Completed')
        ).count()
    }

    # Estadísticas de proyectos
    project_stats = {
        'total': user_projects.count(),
        'completed': user_projects.filter(project_status__status_name='Completed').count(),
        'in_progress': user_projects.filter(project_status__status_name='In Progress').count(),
        'pending': user_projects.filter(project_status__status_name='Created').count(),
    }

    # Estadísticas de eventos
    event_stats = {
        'total': user_events.count(),
        'completed': user_events.filter(event_status__status_name='Completed').count(),
        'in_progress': user_events.filter(event_status__status_name='In Progress').count(),
        'upcoming': user_events.filter(
            Q(updated_at__gte=this_week) &
            ~Q(event_status__status_name='Completed')
        ).count()
    }

    # Actividad reciente (últimos 7 días)
    recent_tasks = user_tasks.filter(updated_at__gte=this_week)[:5]
    recent_projects = user_projects.filter(updated_at__gte=this_week)[:5]
    recent_events = user_events.filter(updated_at__gte=this_week)[:5]

    # System events recientes (últimos 20)
    recent_system_events = SystemEvent.objects.filter(
        timestamp__gte=this_week
    ).select_related('user', 'content_type').order_by('-timestamp')[:20]

    # Items del inbox GTD
    inbox_items = InboxItem.objects.filter(created_by=user, is_processed=False)[:5]

    # Recordatorios próximos
    upcoming_reminders = Reminder.objects.filter(
        created_by=user,
        is_sent=False,
        remind_at__gte=timezone.now(),
        remind_at__lte=timezone.now() + timedelta(days=7)
    ).order_by('remind_at')[:5]

    # Tareas prioritarias (importantes y urgentes)
    priority_tasks = user_tasks.filter(
        Q(important=True) &
        Q(task_status__status_name__in=['To Do', 'In Progress'])
    ).order_by('-important', '-updated_at')[:5]

    # Proyectos activos
    active_projects = user_projects.filter(
        project_status__status_name__in=['In Progress', 'Created']
    ).order_by('-updated_at')[:5]

    # URLs de acceso rápido
    quick_access = {
        'kanban': {'url': 'events:kanban_board', 'title': 'Kanban Board', 'icon': 'bi-kanban', 'color': 'primary'},
        'eisenhower': {'url': 'events:eisenhower_matrix', 'title': 'Eisenhower Matrix', 'icon': 'bi-grid-3x3', 'color': 'warning'},
        'inbox': {'url': 'events:inbox', 'title': 'GTD Inbox', 'icon': 'bi-inbox', 'color': 'info'},
        'templates': {'url': 'events:project_templates', 'title': 'Project Templates', 'icon': 'bi-file-earmark-plus', 'color': 'success'},
        'reminders': {'url': 'events:reminders_dashboard', 'title': 'Reminders', 'icon': 'bi-bell', 'color': 'danger'},
        'dependencies': {'url': 'events:task_dependencies_list', 'title': 'Task Dependencies', 'icon': 'bi-link', 'color': 'secondary'},
    }

    # Agregar panel administrativo de programaciones si el usuario es admin
    if request.user.is_superuser:
        quick_access['schedule_admin'] = {
            'url': 'events:schedule_admin_dashboard',
            'title': 'Admin Programaciones',
            'icon': 'bi-calendar-check',
            'color': 'dark'
        }

    context = {
        'title': 'Dashboard Unificado de Productividad',

        # Estadísticas
        'task_stats': task_stats,
        'project_stats': project_stats,
        'event_stats': event_stats,

        # Datos recientes
        'recent_tasks': recent_tasks,
        'recent_projects': recent_projects,
        'recent_events': recent_events,
        'recent_system_events': recent_system_events,

        # Herramientas específicas
        'inbox_items': inbox_items,
        'upcoming_reminders': upcoming_reminders,
        'priority_tasks': priority_tasks,
        'active_projects': active_projects,

        # URLs de acceso rápido
        'quick_access': quick_access,
    }

    return render(request, 'events/unified_dashboard.html', context)


# ============================================================================
# ROOT DASHBOARD (PANEL DE ADMINISTRACIÓN PRINCIPAL)
# ============================================================================

@login_required
def root(request):
    """
    Vista raíz refactorizada con servicios modulares y mejor mantenibilidad
    """
    # Verificar acceso usando utilidad centralizada
    if not check_root_access(request.user):
        messages.error(request, 'No tienes permisos suficientes para acceder al panel root.')
        return redirect('events:unified_dashboard')

    # Registrar acceso para auditoría
    log_dashboard_access(request.user, 'root_dashboard_access')

    try:
        # Usar el servicio refactorizado para obtener todos los datos
        dashboard = RootDashboardService(request.user, request)
        context = dashboard.get_dashboard_data()

        # Definir bots disponibles con sus tareas predefinidas
        available_bots = [
            {
                'id': 'project_bot',
                'name': 'Bot de Proyectos',
                'description': 'Simula gestión completa de proyectos',
                'icon': 'bi-folder-plus',
                'color': 'primary',
                'tasks': [
                    {'id': 'create_project', 'name': 'Crear Proyecto', 'description': 'Crea un nuevo proyecto con estructura completa'},
                    {'id': 'manage_tasks', 'name': 'Gestionar Tareas', 'description': 'Asigna y administra tareas del proyecto'},
                    {'id': 'generate_reports', 'name': 'Generar Reportes', 'description': 'Crea reportes de progreso del proyecto'},
                    {'id': 'simulate_inbox', 'name': 'Simular Inbox', 'description': 'Crea items de inbox relacionados con el proyecto'}
                ]
            },
            {
                'id': 'teacher_bot',
                'name': 'Bot Profesor',
                'description': 'Simula creación y gestión de cursos educativos',
                'icon': 'bi-mortarboard',
                'color': 'success',
                'tasks': [
                    {'id': 'create_course', 'name': 'Crear Curso', 'description': 'Crea un nuevo curso con estructura básica'},
                    {'id': 'create_lesson', 'name': 'Crear Lección', 'description': 'Añade lecciones al curso'},
                    {'id': 'create_content', 'name': 'Crear Contenido', 'description': 'Genera secciones de contenido educativo'},
                    {'id': 'manage_students', 'name': 'Gestionar Estudiantes', 'description': 'Simula gestión de estudiantes inscritos'}
                ]
            },
            {
                'id': 'client_bot',
                'name': 'Bot Cliente',
                'description': 'Simula interacciones y consultas de clientes',
                'icon': 'bi-person-gear',
                'color': 'info',
                'tasks': [
                    {'id': 'simulate_inbox', 'name': 'Simular Inbox', 'description': 'Crea consultas y tickets de soporte'},
                    {'id': 'send_emails', 'name': 'Enviar Emails', 'description': 'Simula envío de correos electrónicos'},
                    {'id': 'create_tickets', 'name': 'Crear Tickets', 'description': 'Genera tickets de soporte técnico'},
                    {'id': 'simulate_calls', 'name': 'Simular Llamadas', 'description': 'Crea registros de llamadas telefónicas'}
                ]
            }
        ]

        # Añadir elementos finales del contexto
        context.update({
            'title': 'Root Dashboard',
            'page_title': 'Root Dashboard',
            'css_classes': get_responsive_grid_classes(),
            'available_bots': available_bots,
            'available_bots_json': json.dumps(available_bots),
        })

        return render(request, 'events/root.html', context)

    except Exception as e:
        logger.error(f"Error in root dashboard for user {request.user.username}: {str(e)}", exc_info=True)
        messages.error(request, 'Error al cargar el dashboard. Contacte al administrador.')
        return redirect('events:unified_dashboard')


# ============================================================================
# ACCIONES MASIVAS DESDE EL PANEL ROOT
# ============================================================================

@login_required
def root_bulk_actions(request):
    """
    Vista para manejar acciones masivas desde el panel root
    """
    if not check_root_access(request.user):
        return JsonResponse({'success': False, 'error': 'No tienes permisos suficientes'})

    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'})

    action = request.POST.get('action')
    selected_items = request.POST.getlist('selected_items[]')

    # Validación básica de entrada
    if not action:
        return JsonResponse({'success': False, 'error': 'Acción requerida'})

    if not selected_items:
        return JsonResponse({'success': False, 'error': 'No se seleccionaron items'})

    # Limitar número máximo de items por acción para prevenir abuso
    if len(selected_items) > 50:
        return JsonResponse({'success': False, 'error': 'Demasiados items seleccionados (máximo 50)'})

    # Logging para auditoría
    logger.info(f"User {request.user.username} performing bulk action '{action}' on {len(selected_items)} items")

    try:
        items = InboxItem.objects.filter(id__in=selected_items)

        if action == 'mark_processed':
            return _handle_mark_processed(request, items)

        elif action == 'mark_unprocessed':
            return _handle_mark_unprocessed(request, items)

        elif action == 'change_priority':
            return _handle_change_priority(request, items)

        elif action == 'assign_to_user':
            return _handle_assign_to_user(request, items)

        elif action == 'change_category':
            return _handle_change_category(request, items)

        elif action == 'delegate':
            return _handle_delegate(request, items)

        elif action == 'delete':
            return _handle_delete(items)

        else:
            return JsonResponse({'success': False, 'error': 'Acción no válida'})

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


def _handle_mark_processed(request, items):
    """Marca items como procesados"""
    count = 0
    for item in items:
        if not item.is_processed:
            item.is_processed = True
            item.processed_at = timezone.now()
            item.save()
            count += 1

            InboxItemHistory.objects.create(
                inbox_item=item,
                user=request.user,
                action='bulk_mark_processed',
                new_values={'processed_at': item.processed_at.isoformat()}
            )

    return JsonResponse({
        'success': True,
        'message': f'Se marcaron {count} item(s) como procesados',
        'count': count
    })


def _handle_mark_unprocessed(request, items):
    """Marca items como no procesados"""
    count = 0
    for item in items:
        if item.is_processed:
            item.is_processed = False
            item.processed_at = None
            item.save()
            count += 1

            InboxItemHistory.objects.create(
                inbox_item=item,
                user=request.user,
                action='bulk_mark_unprocessed',
                old_values={'processed_at': item.processed_at.isoformat() if item.processed_at else None}
            )

    return JsonResponse({
        'success': True,
        'message': f'Se marcaron {count} item(s) como no procesados',
        'count': count
    })


def _handle_change_priority(request, items):
    """Cambia la prioridad de los items"""
    new_priority = request.POST.get('new_priority')
    if not new_priority or new_priority not in ['alta', 'media', 'baja']:
        return JsonResponse({'success': False, 'error': 'Prioridad inválida'})

    count = items.update(priority=new_priority)

    for item in items:
        InboxItemHistory.objects.create(
            inbox_item=item,
            user=request.user,
            action='bulk_change_priority',
            old_values={'priority': item.priority},
            new_values={'priority': new_priority}
        )

    return JsonResponse({
        'success': True,
        'message': f'Se cambió la prioridad de {count} item(s) a {new_priority}',
        'count': count
    })


def _handle_assign_to_user(request, items):
    """Asigna items a un usuario específico"""
    user_id = request.POST.get('user_id')
    if not user_id:
        return JsonResponse({'success': False, 'error': 'ID de usuario requerido'})

    try:
        target_user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Usuario no encontrado'})

    count = items.update(assigned_to=target_user)

    for item in items:
        InboxItemHistory.objects.create(
            inbox_item=item,
            user=request.user,
            action='bulk_assign_user',
            old_values={'assigned_to': item.assigned_to.username if item.assigned_to else None},
            new_values={'assigned_to': target_user.username}
        )

    return JsonResponse({
        'success': True,
        'message': f'Se asignaron {count} item(s) al usuario {target_user.username}',
        'count': count
    })


def _handle_change_category(request, items):
    """Cambia la categoría GTD de los items"""
    new_category = request.POST.get('new_category')
    if not new_category:
        return JsonResponse({'success': False, 'error': 'Categoría requerida'})

    count = items.update(gtd_category=new_category)

    for item in items:
        InboxItemHistory.objects.create(
            inbox_item=item,
            user=request.user,
            action='bulk_change_category',
            old_values={'gtd_category': item.gtd_category},
            new_values={'gtd_category': new_category}
        )

    return JsonResponse({
        'success': True,
        'message': f'Se cambió la categoría de {count} item(s) a {new_category}',
        'count': count
    })


def _handle_delegate(request, items):
    """Delega items a otro usuario"""
    delegate_user_id = request.POST.get('delegate_user_id')
    if not delegate_user_id:
        return JsonResponse({'success': False, 'error': 'Usuario destino requerido'})

    try:
        delegate_user = User.objects.get(id=delegate_user_id)
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Usuario destino no encontrado'})

    if not delegate_user.is_active:
        return JsonResponse({'success': False, 'error': 'El usuario destino no está activo'})

    # Verificar permisos para delegar
    user_can_delegate = (request.user.is_superuser or
                        (hasattr(request.user, 'cv') and
                         hasattr(request.user.cv, 'role') and
                         request.user.cv.role in ['SU', 'ADMIN', 'GTD_ANALYST']))

    for item in items:
        can_delegate_item = item.created_by == request.user or user_can_delegate
        if not can_delegate_item:
            return JsonResponse({
                'success': False,
                'error': f'No tienes permisos para delegar el item "{item.title}"'
            })

    count = 0
    for item in items:
        old_assigned = item.assigned_to
        item.assigned_to = delegate_user
        item.save(update_fields=['assigned_to'])
        count += 1

        InboxItemHistory.objects.create(
            inbox_item=item,
            user=request.user,
            action='bulk_delegated',
            old_values={'assigned_to': old_assigned.username if old_assigned else None},
            new_values={
                'assigned_to': delegate_user.username,
                'delegation_method': 'bulk_action',
                'delegated_by': request.user.username
            }
        )

    return JsonResponse({
        'success': True,
        'message': f'Se delegaron {count} item(s) al usuario {delegate_user.username}',
        'count': count,
        'delegate_user': delegate_user.username
    })


def _handle_delete(items):
    """Elimina items"""
    count = items.count()
    items.delete()

    return JsonResponse({
        'success': True,
        'message': f'Se eliminaron {count} item(s)',
        'count': count
    })


# ============================================================================
# ÍNDICE DE GESTIÓN (LEGACY)
# ============================================================================

@login_required
def management_index(request):
    """
    Vista índice para la gestión de eventos, proyectos y tareas.
    Muestra estadísticas y enlaces a las diferentes secciones de gestión.
    """
    # Obtener conteos
    event_count = Event.objects.count()
    project_count = Project.objects.count()
    task_count = Task.objects.count()

    # Obtener actividad reciente (últimas 10 modificaciones)
    event_ct = ContentType.objects.get_for_model(Event)
    project_ct = ContentType.objects.get_for_model(Project)
    task_ct = ContentType.objects.get_for_model(Task)

    recent_activities = LogEntry.objects.filter(
        content_type__in=[event_ct, project_ct, task_ct]
    ).select_related('user', 'content_type').order_by('-action_time')[:10]

    # Preparar actividades para el template
    activities = []
    for activity in recent_activities:
        action_map = {
            1: 'Añadido',
            2: 'Modificado',
            3: 'Eliminado'
        }
        activities.append({
            'content_type': activity.content_type,
            'action': action_map.get(activity.action_flag, 'Desconocido'),
            'user': activity.user,
            'timestamp': activity.action_time,
            'object_repr': activity.object_repr
        })

    context = {
        'event_count': event_count,
        'project_count': project_count,
        'task_count': task_count,
        'recent_activities': activities,
    }

    return render(request, 'management/index.html', context)