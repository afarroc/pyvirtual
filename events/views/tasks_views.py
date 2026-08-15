# tasks_views.py - VERSIÓN ORGANIZADA

# ============================================================================
# IMPORTACIONES ESTÁNDAR DE DJANGO
# ============================================================================
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count, Avg, Sum
from django.db import transaction, IntegrityError
from django.http import HttpResponse, Http404, JsonResponse, HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone

# ============================================================================
# IMPORTACIONES DE PYTHON ESTÁNDAR
# ============================================================================
import logging
from decimal import Decimal

# ============================================================================
# IMPORTACIONES DEL PROYECTO
# ============================================================================
from ..models import (
    TaskState, TaskStatus, Project, Task, 
    Event, ProjectStatus, Status
)
from ..utils import statuses_get
from ..utils import update_status, add_credits_to_user

from ..forms import CreateNewTask

# ============================================================================
# CONFIGURACIÓN DE LOGGING
# ============================================================================
logger = logging.getLogger(__name__)


# ============================================================================
# FUNCIONES AUXILIARES DE ESTADOS
# ============================================================================

def get_statuses():
    """
    Obtiene todos los estados del sistema con optimización
    """
    event_statuses = Status.objects.all()
    project_statuses = ProjectStatus.objects.all()
    task_statuses = TaskStatus.objects.all()
    
    return [event_statuses, project_statuses, task_statuses]


def get_tasks_for_user(user):
    """
    Obtiene todas las tareas para un usuario específico con optimización completa
    """
    tasks = Task.objects.filter(
        Q(host=user) | Q(assigned_to=user)
    ).select_related(
        'task_status', 
        'project', 
        'project__project_status',
        'event', 
        'event__event_status',
        'assigned_to',
        'host'
    ).prefetch_related(
        'taskstate_set'
    ).order_by('task_status__status_name', '-updated_at')  # Primero por estado, luego por fecha
    
    tasks_data = []
    active_tasks = []
    completed_tasks = []
    blocked_tasks = []
    
    for task in tasks:
        active_state = task.taskstate_set.filter(
            end_time__isnull=True,
            status__status_name='In Progress'
        ).first()

        completed_state_qs = task.taskstate_set.filter(
            status__status_name='Completed'
        ).order_by('-end_time')
        
        completed_state = completed_state_qs.first() if completed_state_qs.exists() else None
        
        task_data = {
            'task': task,
            'active_state': active_state,
            'completed_state': completed_state,
        }
        
        tasks_data.append(task_data)
        
        if task.task_status.status_name == 'In Progress':
            active_tasks.append(task_data)
        elif task.task_status.status_name == 'Completed':
            completed_tasks.append(task_data)
        elif task.task_status.status_name == 'Blocked':
            blocked_tasks.append(task_data)
    
    # ============================================================
    # CÁLCULO DE ESTADÍSTICAS POR PROYECTO
    # ============================================================
    project_stats = {}
    for task_data in tasks_data:
        task = task_data['task']
        if task.project:
            project_id = task.project.id
            if project_id not in project_stats:
                project_stats[project_id] = {
                    'project': task.project,
                    'total_tasks': 0,
                    'completed_tasks': 0,
                    'in_progress_tasks': 0,
                    'blocked_tasks': 0,
                }
            
            project_stats[project_id]['total_tasks'] += 1
            if task.task_status.status_name == 'Completed':
                project_stats[project_id]['completed_tasks'] += 1
            elif task.task_status.status_name == 'In Progress':
                project_stats[project_id]['in_progress_tasks'] += 1
            elif task.task_status.status_name == 'Blocked':
                project_stats[project_id]['blocked_tasks'] += 1
    
    for project_id, stats in project_stats.items():
        if stats['total_tasks'] > 0:
            stats['completion_rate'] = (stats['completed_tasks'] / stats['total_tasks']) * 100
            stats['progress_rate'] = (stats['in_progress_tasks'] / stats['total_tasks']) * 100
            stats['blocked_rate'] = (stats['blocked_tasks'] / stats['total_tasks']) * 100
        else:
            stats['completion_rate'] = 0
            stats['progress_rate'] = 0
            stats['blocked_rate'] = 0
    
    return tasks_data, active_tasks, completed_tasks, blocked_tasks, project_stats

def render_single_task_view(request, task_id, title, other_task_statuses, statuses):
    """
    Renderiza la vista detallada de una tarea específica con optimización
    """
    try:
        task = get_object_or_404(Task.objects.select_related(
            'task_status', 
            'project', 
            'project__project_status',
            'event', 
            'event__event_status',
            'assigned_to', 
            'host'
        ).prefetch_related('taskstate_set'), id=task_id)
        
        if task.host != request.user and task.assigned_to != request.user:
            messages.error(request, 'No tienes permiso para ver esta tarea.')
            return redirect('events:task_panel')
        
        active_state = task.taskstate_set.filter(
            end_time__isnull=True,
            status__status_name='In Progress'
        ).first()

        completed_state_qs = task.taskstate_set.filter(
            status__status_name='Completed'
        ).order_by('-end_time')
        
        completed_state = completed_state_qs.first() if completed_state_qs.exists() else None
        
        task_data = {
            'task': task,
            'active_state': active_state,
            'completed_state': completed_state,
        }
        
        project_data = None
        if task.project:
            project_tasks = Task.objects.filter(
                project=task.project
            ).select_related(
                'task_status',
                'assigned_to'
            ).order_by('-created_at')[:10]
            
            project_total_tasks = Task.objects.filter(project=task.project).count()
            project_completed_tasks = Task.objects.filter(
                project=task.project,
                task_status__status_name='Completed'
            ).count()
            project_in_progress_tasks = Task.objects.filter(
                project=task.project,
                task_status__status_name='In Progress'
            ).count()
            
            project_data = {
                'project': task.project,
                'active_state': None,
                'related_tasks': project_tasks,
                'total_tasks': project_total_tasks,
                'completed_tasks': project_completed_tasks,
                'in_progress_tasks': project_in_progress_tasks,
                'completion_rate': (project_completed_tasks / project_total_tasks * 100) if project_total_tasks > 0 else 0,
            }
        
        event_data = None
        if task.event:
            event_data = {
                'event': task.event,
                'active_state': None,
            }
        
        alerts = generate_task_alerts(task_data, request.user)
        
        context = {
            'event_statuses': statuses[0],
            'project_statuses': statuses[1],
            'task_statuses': statuses[2],
            'title': f'{title} - {task.title}',
            'task_data': task_data,
            'project_data': project_data,
            'event_data': event_data,
            'alerts': alerts,
            'is_single_task_view': True,
            'other_task_statuses': other_task_statuses,
            'single_task': task,
        }
        
        return render(request, "tasks/task_panel.html", context)
        
    except Exception as e:
        logger.error(f"Error en vista detallada de tarea {task_id}: {str(e)}", exc_info=True)
        messages.error(request, f'Ha ocurrido un error al cargar la tarea: {e}')
        return redirect('events:task_panel')


def render_task_panel_view(request, title, other_task_statuses, statuses, tasks_states):
    """
    Renderiza la vista general del panel de tareas con optimización completa
    """
    try:
        tasks_data, active_tasks, completed_tasks, blocked_tasks, project_stats = get_tasks_for_user(request.user)
        
        total_tasks = len(tasks_data)
        in_progress_count = len(active_tasks)
        completed_count = len(completed_tasks)
        pending_count = sum(1 for task_data in tasks_data 
                           if task_data['task'].task_status.status_name == 'To Do')
        blocked_count = len(blocked_tasks)
        
        total_duration_hours = 0
        completed_with_times = 0
        
        for task_data in completed_tasks:
            if task_data['completed_state'] and task_data['completed_state'].end_time:
                duration = task_data['completed_state'].end_time - task_data['completed_state'].start_time
                total_duration_hours += duration.total_seconds() / 3600
                completed_with_times += 1
        
        avg_completion_hours = total_duration_hours / completed_with_times if completed_with_times > 0 else 0
        
        projects = Project.objects.filter(
            Q(host=request.user) | Q(attendees=request.user)
        ).select_related(
            'project_status'
        ).distinct().order_by('title')
        
        alerts = generate_tasks_overview_alerts(tasks_data, request.user)
        
        performance_alerts = generate_task_performance_alerts(tasks_data, request.user)
        alerts.extend(performance_alerts)
        
        for project_id, stats in project_stats.items():
            if stats['completion_rate'] > 90:
                alerts.append({
                    'type': 'success',
                    'icon': 'bi-trophy',
                    'title': f'¡Proyecto {stats["project"].title} casi listo!',
                    'message': f'{stats["completion_rate"]:.1f}% completado. ¿Listo para finalizar?',
                    'action_url': f'/events/projects/{project_id}/',
                    'action_text': 'Ver proyecto'
                })
            elif stats['blocked_rate'] > 30:
                alerts.append({
                    'type': 'warning',
                    'icon': 'bi-exclamation-triangle',
                    'title': f'Alta tasa de bloqueo en {stats["project"].title}',
                    'message': f'{stats["blocked_rate"]:.1f}% de las tareas están bloqueadas.',
                    'action_url': f'/events/projects/{project_id}/',
                    'action_text': 'Revisar proyecto'
                })
        
        context = {
            'title': f'{title} (User Tasks)',
            'event_statuses': statuses[0],
            'task_statuses': statuses[2],
            'project_statuses': statuses[1],
            'tasks_data': tasks_data,
            'active_tasks': active_tasks,
            'completed_tasks': completed_tasks,
            'blocked_tasks': blocked_tasks,
            'tasks_states': tasks_states,
            'project_stats': project_stats,
            'total_tasks': total_tasks,
            'in_progress_count': in_progress_count,
            'completed_count': completed_count,
            'pending_count': pending_count,
            'blocked_count': blocked_count,
            'avg_completion_hours': avg_completion_hours,
            'projects': projects,
            'alerts': alerts,
            'other_task_statuses': other_task_statuses,
            'is_single_task_view': False,
        }
        
        return render(request, 'tasks/task_panel.html', context)
        
    except Exception as e:
        logger.error(f"Error en panel general de tareas: {str(e)}", exc_info=True)
        messages.error(request, f'Ha ocurrido un error al cargar el panel de tareas: {e}')
        
        context = {
            'title': 'Task Panel',
            'tasks_data': [],
            'alerts': [],
            'is_single_task_view': False,
            'other_task_statuses': other_task_statuses,
        }
        return render(request, 'tasks/task_panel.html', context)


# ============================================================================
# FUNCIONES DE ALERTAS PARA TAREAS
# ============================================================================

def generate_task_alerts(task_data, user):
    """
    Generate contextual alerts for a specific task
    """
    alerts = []
    task = task_data['task']

    if task.updated_at and (timezone.now() - task.updated_at).days > 3:
        alerts.append({
            'type': 'warning',
            'icon': 'bi-exclamation-triangle',
            'title': 'Tarea inactiva',
            'message': f'La tarea "{task.title}" no ha sido actualizada en {(timezone.now() - task.updated_at).days} días.',
            'action_url': f'/events/tasks/edit/{task.id}',
            'action_text': 'Actualizar tarea'
        })

    if task.important and task.task_status.status_name != 'Completed':
        alerts.append({
            'type': 'danger',
            'icon': 'bi-star-fill',
            'title': '¡Prioridad alta!',
            'message': f'La tarea "{task.title}" es de alta prioridad y requiere atención inmediata.',
            'action_url': f'/events/tasks/edit/{task.id}',
            'action_text': 'Revisar prioridad'
        })

    if task.task_status.status_name == 'Blocked':
        alerts.append({
            'type': 'warning',
            'icon': 'bi-slash-circle',
            'title': 'Tarea bloqueada',
            'message': f'La tarea "{task.title}" está bloqueada. Revisa las dependencias.',
            'action_url': f'/events/tasks/edit/{task.id}',
            'action_text': 'Resolver bloqueo'
        })

    if task.project and task.project.project_status.status_name == 'Blocked':
        alerts.append({
            'type': 'danger',
            'icon': 'bi-exclamation-octagon',
            'title': 'Proyecto bloqueado',
            'message': f'El proyecto "{task.project.title}" está bloqueado, afectando esta tarea.',
            'action_url': f'/events/projects/{task.project.id}/',
            'action_text': 'Ver proyecto'
        })

    return alerts


def generate_tasks_overview_alerts(tasks_data, user):
    """
    Generate overview alerts for all tasks
    """
    alerts = []

    if not tasks_data:
        alerts.append({
            'type': 'info',
            'icon': 'bi-info-circle',
            'title': '¡Bienvenido!',
            'message': 'No tienes tareas activas. ¿Quieres crear una nueva?',
            'action_url': '/events/tasks/create/',
            'action_text': 'Crear tarea'
        })
        return alerts

    total_tasks = len(tasks_data)
    completed_tasks = sum(1 for task in tasks_data if task['task'].task_status.status_name == 'Completed')
    in_progress_tasks = sum(1 for task in tasks_data if task['task'].task_status.status_name == 'In Progress')
    pending_tasks = sum(1 for task in tasks_data if task['task'].task_status.status_name == 'To Do')

    if total_tasks > 0:
        completion_rate = (completed_tasks / total_tasks) * 100
        if completion_rate < 30:
            alerts.append({
                'type': 'danger',
                'icon': 'bi-graph-down',
                'title': 'Bajo progreso general',
                'message': f'Solo {completion_rate:.1f}% de las tareas completadas ({completed_tasks}/{total_tasks}).',
                'action_url': '/events/tasks/',
                'action_text': 'Ver todas las tareas'
            })
        elif completion_rate > 80:
            alerts.append({
                'type': 'success',
                'icon': 'bi-trophy',
                'title': '¡Excelente progreso!',
                'message': f'{completion_rate:.1f}% de las tareas completadas. ¡Sigue así!',
                'action_url': '/events/tasks/',
                'action_text': 'Ver estadísticas'
            })

    if in_progress_tasks > 5:
        alerts.append({
            'type': 'warning',
            'icon': 'bi-exclamation-circle',
            'title': 'Demasiadas tareas activas',
            'message': f'Tienes {in_progress_tasks} tareas en progreso. Considera priorizar.',
            'action_url': '/events/tasks/',
            'action_text': 'Gestionar prioridades'
        })

    high_priority_tasks = [task for task in tasks_data if task['task'].important and task['task'].task_status.status_name != 'Completed']
    if high_priority_tasks:
        alerts.append({
            'type': 'danger',
            'icon': 'bi-star-fill',
            'title': 'Tareas prioritarias pendientes',
            'message': f'{len(high_priority_tasks)} tarea(s) de alta prioridad requieren atención.',
            'action_url': '/events/tasks/',
            'action_text': 'Revisar prioridades'
        })

    blocked_tasks = [task for task in tasks_data if task['task'].task_status.status_name == 'Blocked']
    if blocked_tasks:
        alerts.append({
            'type': 'warning',
            'icon': 'bi-slash-circle',
            'title': 'Tareas bloqueadas',
            'message': f'{len(blocked_tasks)} tarea(s) están bloqueadas y necesitan resolución.',
            'action_url': '/events/tasks/',
            'action_text': 'Resolver bloqueos'
        })

    recent_tasks = [task for task in tasks_data if task['task'].created_at > timezone.now() - timezone.timedelta(days=3)]
    if recent_tasks:
        alerts.append({
            'type': 'info',
            'icon': 'bi-calendar-plus',
            'title': 'Actividad reciente',
            'message': f'{len(recent_tasks)} tarea(s) creada(s) en los últimos 3 días.',
            'action_url': '/events/tasks/',
            'action_text': 'Ver tareas nuevas'
        })

    return alerts


def generate_task_performance_alerts(tasks_data, user):
    """
    Generate performance-based alerts for tasks
    """
    alerts = []

    if not tasks_data:
        return alerts

    completed_tasks = [task for task in tasks_data if task['task'].task_status.status_name == 'Completed']
    if completed_tasks:
        recent_completed = [task for task in completed_tasks if task['task'].updated_at > timezone.now() - timezone.timedelta(days=7)]
        if recent_completed:
            alerts.append({
                'type': 'success',
                'icon': 'bi-speedometer2',
                'title': 'Buena velocidad de trabajo',
                'message': f'Has completado {len(recent_completed)} tarea(s) en la última semana.',
                'action_url': '/events/tasks/',
                'action_text': 'Ver progreso'
            })

    project_task_counts = {}
    for task_data in tasks_data:
        project_id = task_data['task'].project.id if task_data['task'].project else 'no_project'
        project_name = task_data['task'].project.title if task_data['task'].project else 'Sin proyecto'
        if project_id not in project_task_counts:
            project_task_counts[project_id] = {'name': project_name, 'count': 0}
        project_task_counts[project_id]['count'] += 1

    for project_info in project_task_counts.values():
        if project_info['count'] > 15:
            alerts.append({
                'type': 'warning',
                'icon': 'bi-list-check',
                'title': 'Proyecto sobrecargado',
                'message': f'El proyecto "{project_info["name"]}" tiene {project_info["count"]} tareas. Considera dividir el trabajo.',
                'action_url': '/events/projects/',
                'action_text': 'Revisar proyecto'
            })

    return alerts


# ============================================================================
# VISTA PRINCIPAL DE TAREAS
# ============================================================================

@login_required
def tasks(request, task_id=None, project_id=None):
    """
    Vista principal de tareas - maneja listado y detalle
    """
    title = 'Tasks'
    
    urls = [
        {'url_name': 'events:task_create', 'name': 'Task Create'},
        {'url_name': 'events:task_edit', 'name': 'Task Edit'},
    ]
    
    other_urls = [
        {'url_name': 'events:events', 'id': None, 'name': 'Events Panel'},
        {'url_name': 'events:projects', 'id': None, 'name': 'Projects Panel'},
        {'url_name': 'events:tasks', 'id': None, 'name': 'Tasks Panel'},
    ]
    
    instructions = [
        {'instruction': 'Fill carefully the metadata.', 'name': 'Form'},
    ]
    
    task_statuses = TaskStatus.objects.all().order_by('status_name')

    if task_id:
        task = get_object_or_404(Task, id=task_id)
        task_data = {'task': task}
        alerts = generate_task_alerts(task_data, request.user)

        return render(request, "tasks/task_detail.html", {
            'title': title,
            'task': task,
            'task_statuses': task_statuses,
            'alerts': alerts,
        })

    else:
        if not project_id:
            tasks_list = Task.objects.filter(
                Q(host=request.user) | Q(assigned_to=request.user)
            ).select_related(
                'task_status', 
                'project', 
                'project__project_status',
                'event', 
                'event__event_status',
                'assigned_to',
                'host'
            ).prefetch_related(
                'taskstate_set'
            ).order_by('task_status__status_name', '-updated_at')  # CORREGIDO: primero por estado, luego por última actualización
        else:
            tasks_list = Task.objects.filter(
                Q(host=request.user) | Q(assigned_to=request.user), 
                project_id=project_id
            ).select_related(
                'task_status', 
                'project', 
                'project__project_status',
                'event', 
                'event__event_status',
                'assigned_to',
                'host'
            ).prefetch_related(
                'taskstate_set'
            ).order_by('task_status__status_name', '-updated_at')  # CORREGIDO: primero por estado, luego por última actualización

        tasks_data = []
        for task in tasks_list:
            active_state = task.taskstate_set.filter(
                end_time__isnull=True,
                status__status_name='In Progress'
            ).first()

            completed_state_qs = task.taskstate_set.filter(
                status__status_name='Completed'
            ).order_by('-end_time')
            
            completed_state = completed_state_qs.first() if completed_state_qs.exists() else None
            
            task_data = {
                'task': task,
                'active_state': active_state,
                'completed_state': completed_state,
            }
            
            tasks_data.append(task_data)

        alerts = generate_tasks_overview_alerts(tasks_data, request.user)

        performance_alerts = generate_task_performance_alerts(tasks_data, request.user)
        alerts.extend(performance_alerts)

        other_task_statuses = TaskStatus.objects.exclude(
            status_name__in=['In Progress', 'Completed']
        )

        return render(request, "tasks/tasks.html", {
            'title': title,
            'tasks': tasks_list,
            'tasks_data': tasks_data,
            'alerts': alerts,
            'task_statuses': task_statuses,
            'other_task_statuses': other_task_statuses,
        })

# ============================================================================
# VISTA PANEL DE TAREAS
# ============================================================================

@login_required
def task_panel(request, task_id=None):
    """
    Vista principal del panel de tareas - VERSIÓN COMPLETAMENTE OPTIMIZADA
    """
    title = "Task Panel"
    
    statuses = statuses_get()
    
    tasks_states = TaskState.objects.select_related(
        'task', 
        'task__task_status',
        'task__project',
        'task__project__project_status',
        'task__event',
        'task__assigned_to'
    ).order_by('-start_time')[:10]
    
    all_task_statuses = TaskStatus.objects.all()
    other_task_statuses = all_task_statuses.exclude(
        status_name__in=['In Progress', 'Completed']
    )
    
    if task_id:
        return render_single_task_view(
            request, task_id, title, other_task_statuses, statuses
        )
    
    return render_task_panel_view(
        request, title, other_task_statuses, statuses, tasks_states
    )


# ============================================================================
# VISTAS CRUD DE TAREAS
# ============================================================================

@login_required
def task_create(request, project_id=None):
    """
    Vista para crear una nueva tarea
    """
    title = "Create New Task"
    
    if request.method == 'GET':
        try:
            initial_status_name = 'To Do'
            initial_task_status = get_object_or_404(TaskStatus, status_name=initial_status_name)
        except Exception as e:
            messages.error(request, f"Error al obtener estado de tarea: {e}")
            return redirect('events:task_panel')
        
        initial_ticket_price = 0.07
        
        if project_id:
            form = CreateNewTask(initial={
                'project': project_id,
                'task_status': initial_task_status,
                'assigned_to': request.user,
                'ticket_price': initial_ticket_price,
            })
        else:
            form = CreateNewTask(initial={
                'project': project_id,
                'task_status': initial_task_status,
                'assigned_to': request.user,
                'ticket_price': initial_ticket_price,
            })

    else:
        print('POST data:', request.POST)
        form = CreateNewTask(request.POST)
        
        if form.is_valid():
            task = form.save(commit=False)
            task.host = request.user
            task.assigned_to = form.cleaned_data.get('assigned_to') or request.user
            task.event = form.cleaned_data.get('event')

            try:
                with transaction.atomic():
                    task.save()
                    form.save_m2m()
                    messages.success(request, 'Tarea creada exitosamente!')
                    
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({'success': True, 'message': 'Tarea creada exitosamente!', 'task_id': task.id})
                    return redirect('events:task_panel')
                
            except IntegrityError as e:
                error_msg = f'Hubo un problema al guardar la tarea: {e}'
                messages.error(request, error_msg)
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': error_msg}, status=400)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.method == 'POST':
        return JsonResponse({'success': False, 'error': 'Error de validación del formulario'}, status=400)
    
    return render(request, 'tasks/task_create.html', {
        'form': form,
        'title': title,
    })


@login_required
def task_edit(request, task_id=None):
    """
    Vista para editar una tarea existente
    """
    try:
        if task_id is not None:
            try:
                task = get_object_or_404(Task, pk=task_id)
            except Http404:
                messages.error(request, 'La Tarea con el ID "{}" no existe.'.format(task_id))
                return redirect('home')

            if request.method == 'POST':
                form = CreateNewTask(request.POST, instance=task)
                if form.is_valid():
                    task.editor = request.user
                    print('guardando via post si es valido')

                    for field in form.changed_data:
                        old_value = getattr(task, field)
                        new_value = form.cleaned_data.get(field)
                        task.record_edit(
                            editor=request.user,
                            field_name=field,
                            old_value=str(old_value),
                            new_value=str(new_value)
                        )
                    form.save()

                    messages.success(request, 'Tarea guardada con éxito.')
                    return redirect('events:task_panel')
                else:
                    messages.error(request, 'Hubo un error al guardar la tarea. Por favor, revisa el formulario.')
            else:
                form = CreateNewTask(instance=task)
            
            return render(request, 'tasks/task_edit.html', {'form': form, 'task': task})
        
        else:
            if request.user.is_superuser or (hasattr(request.user, 'cv') and getattr(request.user.cv, 'role', None) == 'SU'):
                tasks = Task.objects.all().order_by('-created_at')
            else:
                tasks = Task.objects.filter(Q(assigned_to=request.user) | Q(project__attendees=request.user)).distinct().order_by('-created_at')
            
            return render(request, 'tasks/task_list.html', {'tasks': tasks})
    
    except Exception as e:
        messages.error(request, 'Ha ocurrido un error: {}'.format(e))
        return redirect('home')


@login_required
def task_delete(request, task_id):
    """
    Vista para eliminar una tarea
    """
    if request.method == 'POST':
        task = get_object_or_404(Task, pk=task_id)
        if not (request.user.is_superuser or (hasattr(request.user, 'cv') and getattr(request.user.cv, 'role', None) == 'SU')):
            messages.error(request, 'No tienes permiso para eliminar esta tarea.')
            return redirect('events:tasks')
        
        task.delete()
        messages.success(request, 'La tarea ha sido eliminada exitosamente.')
    else:
        messages.error(request, 'Método no permitido.')
    
    return redirect('events:tasks')


@login_required
def task_delete_ajax(request, task_id):
    """
    AJAX endpoint para eliminar una tarea y devolver datos actualizados de la lista
    """
    logger = logging.getLogger(__name__)
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)
    
    try:
        task = get_object_or_404(Task, pk=task_id)
        
        if not (request.user.is_superuser or (hasattr(request.user, 'cv') and getattr(request.user.cv, 'role', None) == 'SU')):
            return JsonResponse({'success': False, 'error': 'No tienes permiso para eliminar esta tarea.'}, status=403)
        
        task_title = task.title
        task.delete()
        logger.info(f"Task {task_id} deleted by {request.user.username}")
        
        tasks_list = Task.objects.filter(
            Q(host=request.user) | Q(assigned_to=request.user)
        ).select_related(
            'task_status', 
            'project', 
            'project__project_status',
            'event', 
            'event__event_status',
            'assigned_to',
            'host'
        ).prefetch_related('taskstate_set').order_by('task_status__status_name', '-updated_at')
        
        tasks_data = []
        for task in tasks_list:
            active_state = task.taskstate_set.filter(
                end_time__isnull=True,
                status__status_name='In Progress'
            ).first()
            
            completed_state_qs = task.taskstate_set.filter(
                status__status_name='Completed'
            ).order_by('-end_time')
            
            completed_state = completed_state_qs.first() if completed_state_qs.exists() else None
            
            tasks_data.append({
                'id': task.id,
                'title': task.title,
                'status': task.task_status.status_name if task.task_status else '',
                'project': task.project.title if task.project else '',
                'assigned_to': task.assigned_to.username if task.assigned_to else '',
                'important': task.important,
                'created_at': task.created_at.strftime('%Y-%m-%d'),
            })
        
        total_tasks = len(tasks_data)
        in_progress_count = sum(1 for t in tasks_data if t['status'] == 'In Progress')
        completed_count = sum(1 for t in tasks_data if t['status'] == 'Completed')
        high_priority_count = sum(1 for t in tasks_data if t['important'])
        
        return JsonResponse({
            'success': True,
            'message': f'Tarea "{task_title}" eliminada exitosamente.',
            'tasks': tasks_data,
            'stats': {
                'total_tasks': total_tasks,
                'in_progress_count': in_progress_count,
                'completed_count': completed_count,
                'high_priority_count': high_priority_count,
            }
        })
        
    except Exception as e:
        logger.error(f"Error deleting task {task_id}: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ============================================================================
# VISTAS DE ACCIONES SOBRE TAREAS
# ============================================================================

@login_required
def change_task_status(request, task_id):
    """
    Vista para cambiar el estado de una tarea
    """
    try:
        if request.method != 'POST':
            return HttpResponse("Método no permitido", status=405)
        
        task = get_object_or_404(Task, pk=task_id)
        new_status_id = request.POST.get('new_status_id')
        new_status = get_object_or_404(TaskStatus, pk=new_status_id)
        
        if request.user is None:
            messages.error(request, "User is none: Usuario no autenticado")
            return redirect('home')
        
        if task.host is not None and (task.host == request.user or request.user in task.attendees.all()):
            old_status = task.task_status
            task.record_edit(
                editor=request.user,
                field_name='task_status',
                old_value=str(old_status),
                new_value=str(new_status)
            )
        else:
            return HttpResponse("No tienes permiso para editar este task", status=403)
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return HttpResponse(f"Error: {str(e)}", status=500)
    
    messages.success(request, 'Task status edited successfully!')
    return redirect('events:task_panel')


@login_required
def task_activate(request, task_id=None):
    """
    Vista para activar/completar tareas y manejar créditos
    """
    switch = 'In Progress'
    title = 'Task Activate'
    
    if task_id:
        task = get_object_or_404(Task, pk=task_id)
        event = task.event
        project = task.project
        project_event = project.event
        amount = 0
        
        if task.task_status.status_name == switch:
            switch = 'Completed'
            amount += 1           

        try:
            new_task_status = TaskStatus.objects.get(status_name=switch)
            update_status(task, 'task_status', new_task_status, request.user)
            messages.success(request, f'La tarea ha sido cambiada a estado {switch} exitosamente.')

            new_event_status = Status.objects.get(status_name=switch)
            update_status(event, 'event_status', new_event_status, request.user)
            messages.success(request, f'El evento de la tarea ha sido cambiado a estado {switch} exitosamente.')

            tasks_in_progress = Task.objects.filter(project_id=project.id, task_status__status_name='In Progress')

            if switch == 'Completed' and tasks_in_progress.exists():
                messages.success(request, f'There are tasks in progress: {tasks_in_progress}')
            else:
                new_project_status = ProjectStatus.objects.get(status_name=switch)
                update_status(project, 'project_status', new_project_status, request.user)
                messages.success(request, f'El proyecto ha sido cambiado a estado {switch} exitosamente.')
                
                update_status(project_event, 'event_status', new_event_status, request.user)
                messages.success(request, f'El evento del proyecto ha sido cambiado a estado {switch} exitosamente.')

            if task.task_status.status_name == "Completed":
                task_state = TaskState.objects.filter(
                    task=task,
                    status__status_name='In Progress'
                ).latest('start_time')
                
                if task_state.end_time:
                    elapsed_time = (task_state.end_time - task_state.start_time).total_seconds()
            else:
                elapsed_time = 0

            elapsed_minutes = Decimal(elapsed_time) / Decimal(60)
            total_cost = elapsed_minutes * task.ticket_price
            print(total_cost)
            amount += total_cost
            
            if amount > 0:
                success, message = add_credits_to_user(request.user, amount)
                if success:
                    messages.success(request, f"Commission:")
                    messages.success(request, message)
                    messages.success(request, f"Total Credits: {request.user.creditaccount.balance}")
                else:
                    return render(request, 'credits/add_credits.html', {'error': message})
        
        except TaskStatus.DoesNotExist:
            messages.error(request, 'El estado "En Curso" no existe en la base de datos.')
        except TaskState.DoesNotExist:
            messages.error(request, 'No se encontró un estado "En Curso" para la tarea.')
        except Exception as e:
            messages.error(request, f'Ocurrió un error al intentar activar la tarea: {e}')
        
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
    
    else:
        tasks = Task.objects.all().order_by('-updated_at')
        try:
            return render(request, "tasks/task_activate.html",{
                'title': f'{title} (No ID)',
                'tasks': tasks,
            })
        except Exception as e:
            messages.error(request, f'Ha ocurrido un error: {e}')
            return redirect('events:task_panel')


# ============================================================================
# VISTAS AJAX Y UTILITARIAS
# ============================================================================

@login_required
def task_change_status_ajax(request):
    """
    AJAX endpoint to change task status (with project/event cascade updates)
    """
    logger.debug(f"task_change_status_ajax: Método de solicitud = {request.method}")
    logger.debug(f"task_change_status_ajax: Usuario autenticado = {request.user.username} (ID: {request.user.id})")
    
    if request.method == 'POST':
        try:
            logger.debug(f"task_change_status_ajax: Parámetros POST recibidos = {dict(request.POST)}")
            
            task_id = request.POST.get('task_id')
            new_status_name = request.POST.get('new_status_name')
            action = request.POST.get('action')
            
            logger.debug(f"task_change_status_ajax: Parámetros iniciales - task_id='{task_id}', new_status_name='{new_status_name}', action='{action}'")
            
            if not task_id:
                logger.error("task_change_status_ajax: No se proporcionó task_id en la solicitud")
                return JsonResponse({'success': False, 'error': 'Task ID is required'})
            
            if not new_status_name and action:
                logger.debug(f"task_change_status_ajax: Determinando estado basado en action='{action}'")
                if action == 'activate':
                    new_status_name = 'In Progress'
                elif action == 'deactivate':
                    new_status_name = 'To Do'
                else:
                    logger.error(f"task_change_status_ajax: Acción desconocida '{action}'")
                    return JsonResponse({'success': False, 'error': f'Acción desconocida: {action}'})
            
            if not new_status_name:
                logger.error("task_change_status_ajax: No se pudo determinar el nuevo estado")
                return JsonResponse({'success': False, 'error': 'No se pudo determinar el nuevo estado'})
            
            logger.debug(f"task_change_status_ajax: Estado final determinado = '{new_status_name}'")
            
            logger.debug(f"task_change_status_ajax: Buscando tarea con ID={task_id}")
            task = get_object_or_404(Task, id=task_id)
            logger.debug(f"task_change_status_ajax: Tarea encontrada - ID: {task.id}, Título: '{task.title}', Estado actual: '{task.task_status.status_name}'")
            logger.debug(f"task_change_status_ajax: Proyecto asociado: {task.project}, Evento asociado: {task.event}")

            logger.debug(f"task_change_status_ajax: Verificando permisos - Host: {task.host}, Usuario actual: {request.user}")
            if task.host != request.user and request.user not in task.attendees.all():
                logger.warning(f"task_change_status_ajax: Permiso denegado para usuario {request.user.username}")
                return JsonResponse({'success': False, 'error': 'Permission denied'})
            logger.debug("task_change_status_ajax: Permisos validados correctamente")

            logger.debug(f"task_change_status_ajax: Buscando estado '{new_status_name}'")
            try:
                new_status = TaskStatus.objects.get(status_name=new_status_name)
            except TaskStatus.DoesNotExist:
                logger.error(f"task_change_status_ajax: Estado '{new_status_name}' no existe")
                return JsonResponse({'success': False, 'error': f"TaskStatus '{new_status_name}' does not exist"}, status=400)
            logger.debug(f"task_change_status_ajax: Nuevo estado encontrado - ID: {new_status.id}, Nombre: '{new_status.status_name}'")

            old_status = task.task_status
            logger.info(f"task_change_status_ajax: Cambiando estado de tarea {task.id} de '{old_status}' a '{new_status}'")
            
            task.record_edit(
                editor=request.user,
                field_name='task_status',
                old_value=str(old_status),
                new_value=str(new_status)
            )
            logger.debug("task_change_status_ajax: Cambio registrado en el historial")

            task.task_status = new_status
            task.save()
            logger.debug(f"task_change_status_ajax: Tarea actualizada en base de datos")

            if task.event:
                logger.debug(f"task_change_status_ajax: Actualizando evento asociado - ID: {task.event.id}")
                try:
                    new_event_status = Status.objects.get(status_name=new_status_name)
                    update_status(task.event, 'event_status', new_event_status, request.user)
                    logger.info(f"task_change_status_ajax: Evento {task.event.id} actualizado a '{new_status_name}'")
                except Status.DoesNotExist:
                    logger.warning(f"task_change_status_ajax: Estado '{new_status_name}' no existe para eventos")
                except Exception as e:
                    logger.error(f"task_change_status_ajax: Error actualizando evento: {e}")

            # ============================================================
            # LÓGICA CORREGIDA PARA ACTUALIZACIÓN DE PROYECTO
            # ============================================================
            if task.project:
                logger.debug(f"task_change_status_ajax: Verificando proyecto asociado - ID: {task.project.id}")
                
                # Obtener todas las tareas del proyecto
                all_project_tasks = Task.objects.filter(project_id=task.project.id)
                
                # Contar tareas por estado
                total_tasks = all_project_tasks.count()
                completed_tasks = all_project_tasks.filter(task_status__status_name='Completed').count()
                in_progress_tasks = all_project_tasks.filter(task_status__status_name='In Progress').count()
                blocked_tasks = all_project_tasks.filter(task_status__status_name='Blocked').count()
                to_do_tasks = all_project_tasks.filter(task_status__status_name='To Do').count()
                
                logger.debug(f"task_change_status_ajax: Estadísticas del proyecto - Total: {total_tasks}, Completadas: {completed_tasks}, En progreso: {in_progress_tasks}, Bloqueadas: {blocked_tasks}, To Do: {to_do_tasks}")
                
                try:
                    # REGLA 1: Si hay tareas bloqueadas → proyecto BLOQUEADO
                    if blocked_tasks > 0:
                        logger.debug(f"task_change_status_ajax: Hay tareas bloqueadas ({blocked_tasks}), proyecto a 'Blocked'")
                        new_project_status = ProjectStatus.objects.get(status_name='Blocked')
                        update_status(task.project, 'project_status', new_project_status, request.user)
                        
                        if task.project.event:
                            new_event_status = Status.objects.get(status_name='Blocked')
                            update_status(task.project.event, 'event_status', new_event_status, request.user)
                    
                    # REGLA 2: Si NO hay tareas bloqueadas Y hay tareas en progreso → proyecto EN PROGRESO
                    elif in_progress_tasks > 0:
                        logger.debug(f"task_change_status_ajax: Hay tareas en progreso ({in_progress_tasks}), proyecto a 'In Progress'")
                        new_project_status = ProjectStatus.objects.get(status_name='In Progress')
                        update_status(task.project, 'project_status', new_project_status, request.user)
                        
                        if task.project.event:
                            new_event_status = Status.objects.get(status_name='In Progress')
                            update_status(task.project.event, 'event_status', new_event_status, request.user)
                    
                    # REGLA 3: Si NO hay tareas bloqueadas, NO hay en progreso, Y todas están completadas → proyecto COMPLETADO
                    elif completed_tasks == total_tasks and total_tasks > 0:
                        logger.debug(f"task_change_status_ajax: TODAS las tareas completadas ({completed_tasks}/{total_tasks}), proyecto a 'Completed'")
                        new_project_status = ProjectStatus.objects.get(status_name='Completed')
                        update_status(task.project, 'project_status', new_project_status, request.user)
                        
                        if task.project.event:
                            new_event_status = Status.objects.get(status_name='Completed')
                            update_status(task.project.event, 'event_status', new_event_status, request.user)
                    
                    # REGLA 4: En cualquier otro caso (tareas pendientes sin progreso) → proyecto TO DO
                    else:
                        logger.debug(f"task_change_status_ajax: Sin tareas en progreso ni bloqueadas, con pendientes, proyecto a 'To Do'")
                        new_project_status = ProjectStatus.objects.get(status_name='To Do')
                        update_status(task.project, 'project_status', new_project_status, request.user)
                        
                        if task.project.event:
                            new_event_status = Status.objects.get(status_name='To Do')
                            update_status(task.project.event, 'event_status', new_event_status, request.user)
                
                except Exception as e:
                    logger.error(f"task_change_status_ajax: Error actualizando proyecto: {e}")

            # ============================================================
            # CÁLCULO DE CRÉDITOS PARA TAREAS COMPLETADAS
            # ============================================================
            if new_status_name == "Completed":
                logger.debug(f"task_change_status_ajax: Tarea completada, calculando créditos")
                try:
                    task_state = TaskState.objects.filter(
                        task=task,
                        status__status_name='In Progress'
                    ).latest('start_time')
                    
                    if task_state.end_time:
                        elapsed_time = (task_state.end_time - task_state.start_time).total_seconds()
                        elapsed_minutes = Decimal(elapsed_time) / Decimal(60)
                        total_cost = elapsed_minutes * task.ticket_price
                        
                        logger.debug(f"task_change_status_ajax: Tiempo transcurrido: {elapsed_time}s = {elapsed_minutes} min")
                        logger.debug(f"task_change_status_ajax: Costo total: {total_cost} (ticket_price: {task.ticket_price})")
                        
                        if total_cost > 0:
                            success, message = add_credits_to_user(request.user, total_cost)
                            if success:
                                logger.info(f"task_change_status_ajax: Créditos añadidos: {total_cost}, Mensaje: {message}")
                            else:
                                logger.error(f"task_change_status_ajax: Error añadiendo créditos: {message}")
                except TaskState.DoesNotExist:
                    logger.warning(f"task_change_status_ajax: No se encontró estado 'In Progress' para calcular créditos")
                except Exception as e:
                    logger.error(f"task_change_status_ajax: Error calculando créditos: {e}")

            logger.info(f"task_change_status_ajax: Estado de tarea {task.id} actualizado exitosamente por {request.user.username}")
            return JsonResponse({
                'success': True, 
                'message': f'Task status updated to {new_status_name}',
                'task_id': task_id,
                'old_status': str(old_status),
                'new_status': str(new_status),
                'project_updated': task.project is not None,
                'event_updated': task.event is not None
            })

        except Exception as e:
            logger.exception(f"task_change_status_ajax: Error inesperado - {str(e)}")
            return JsonResponse({
                'success': False, 
                'error': str(e),
                'task_id': task_id if 'task_id' in locals() else None,
                'new_status_name': new_status_name if 'new_status_name' in locals() else None
            })

    logger.warning(f"task_change_status_ajax: Método {request.method} no permitido")
    return JsonResponse({'success': False, 'error': 'Invalid request method'})
@login_required
def task_export(request):
    """
    Export tasks data to CSV
    """
    import csv
    from django.http import HttpResponse

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="tasks_export.csv"'

    writer = csv.writer(response)
    writer.writerow(['ID', 'Title', 'Description', 'Status', 'Project', 'Assigned To', 'Created At'])

    tasks = Task.objects.all().select_related('task_status', 'project', 'assigned_to')
    for task in tasks:
        writer.writerow([
            task.id,
            task.title,
            task.description or '',
            task.task_status.status_name if task.task_status else '',
            task.project.title if task.project else '',
            task.assigned_to.username if task.assigned_to else '',
            task.created_at.strftime('%Y-%m-%d %H:%M:%S')
        ])

    return response


@login_required
def task_bulk_action(request):
    """
    Handle bulk actions for tasks
    """
    if request.method == 'POST':
        action = request.POST.get('action')
        selected_tasks = request.POST.getlist('selected_items')

        if not selected_tasks:
            messages.error(request, 'No tasks selected.')
            return redirect('events:task_panel')

        tasks = Task.objects.filter(id__in=selected_tasks)

        if action == 'delete':
            count = tasks.count()
            tasks.delete()
            messages.success(request, f'Successfully deleted {count} task(s).')
        elif action == 'activate':
            count = tasks.update(task_status=TaskStatus.objects.get(status_name='In Progress'))
            messages.success(request, f'Successfully activated {count} task(s).')
        elif action == 'complete':
            count = tasks.update(task_status=TaskStatus.objects.get(status_name='Completed'))
            messages.success(request, f'Successfully completed {count} task(s).')

    return redirect('events:task_panel')