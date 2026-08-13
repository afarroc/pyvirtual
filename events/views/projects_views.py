# events/projects_views.py - IMPORTACIONES CORREGIDAS

# Django y estándar
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count
from django.utils import timezone
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect, Http404
from django.urls import reverse
from django.db import transaction, IntegrityError
import logging
import csv

from ..my_utils import statuses_get
# Modelos locales
from ..models import (
    Project, Task, Event,
    ProjectStatus, TaskStatus, Status
)

# Formularios locales
from ..forms import CreateNewProject

# Gestión de proyectos
from ..management.project_manager import ProjectManager

logger = logging.getLogger(__name__)

def get_projects_for_user(user):
    """
    Obtiene todos los proyectos para un usuario específico con optimización completa
    """
    projects = Project.objects.filter(
        Q(host=user) | Q(attendees=user)
    ).select_related(
        'project_status', 
        'event', 
        'host', 
        'assigned_to'
    ).prefetch_related(
        'attendees',
        'task_set'
    ).order_by('-created_at')
    
    projects_data = []
    active_projects = []
    completed_projects = []
    blocked_projects = []
    
    for project in projects:
        # Contar tareas del proyecto
        count_tasks = project.task_set.count()
        
        # Obtener tareas del proyecto con sus estados
        project_tasks = project.task_set.select_related('task_status').all()
        
        # Calcular estadísticas de tareas
        completed_tasks = project_tasks.filter(task_status__status_name='Completed').count()
        in_progress_tasks = project_tasks.filter(task_status__status_name='In Progress').count()
        
        project_data = {
            'project': project,
            'count_tasks': count_tasks,
            'tasks': project_tasks,
            'completed_tasks': completed_tasks,
            'in_progress_tasks': in_progress_tasks,
        }
        
        projects_data.append(project_data)
        
        # Clasificar proyectos por estado
        if project.project_status.status_name == 'In Progress':
            active_projects.append(project_data)
        elif project.project_status.status_name == 'Completed':
            completed_projects.append(project_data)
        elif project.project_status.status_name == 'Blocked':
            blocked_projects.append(project_data)
    
    return projects_data, active_projects, completed_projects, blocked_projects


def render_single_project_view(request, project_id, title, statuses):
    """
    Renderiza la vista detallada de un proyecto específico con optimización
    """
    try:
        # Obtener proyecto con optimización de consultas
        project = get_object_or_404(Project.objects.select_related(
            'project_status', 
            'event', 
            'host', 
            'assigned_to'
        ).prefetch_related(
            'attendees',
            'task_set'
        ), id=project_id)
        
        # Verificar permisos
        if project.host != request.user and request.user not in project.attendees.all():
            messages.error(request, 'No tienes permiso para ver este proyecto.')
            return redirect('events:project_panel')
        
        # Obtener tareas del proyecto
        tasks = project.task_set.select_related(
            'task_status', 
            'assigned_to'
        ).order_by('-created_at')
        
        # Calcular estadísticas del proyecto
        total_tasks = tasks.count()
        completed_tasks = tasks.filter(task_status__status_name='Completed').count()
        in_progress_tasks = tasks.filter(task_status__status_name='In Progress').count()
        pending_tasks = tasks.filter(task_status__status_name='To Do').count()
        
        # Calcular porcentaje de completado
        completion_rate = 0
        if total_tasks > 0:
            completion_rate = (completed_tasks / total_tasks) * 100
        
        # Preparar datos del proyecto
        project_data = {
            'project': project,
            'tasks': tasks,
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'in_progress_tasks': in_progress_tasks,
            'pending_tasks': pending_tasks,
            'completion_rate': completion_rate,
        }
        
        # Generar alertas
        alerts = generate_project_alerts(project_data, request.user)
        
        context = {
            'event_statuses': statuses[0],
            'project_statuses': statuses[1],
            'task_statuses': statuses[2],
            'title': f'{title} - {project.title}',
            'project_data': project_data,
            'alerts': alerts,
            'is_single_project_view': True,
            'single_project': project,
        }
        
        return render(request, "projects/project_panel.html", context)
        
    except Exception as e:
        logger.error(f"Error en vista detallada de proyecto {project_id}: {str(e)}", exc_info=True)
        messages.error(request, f'Ha ocurrido un error al cargar el proyecto: {e}')
        return redirect('events:project_panel')


def render_project_panel_view(request, title, statuses):
    """
    Renderiza la vista general del panel de proyectos con optimización completa
    """
    try:
        # Obtener todos los proyectos del usuario con estadísticas
        projects_data, active_projects, completed_projects, blocked_projects = get_projects_for_user(request.user)
        
        # Calcular estadísticas generales
        total_projects = len(projects_data)
        in_progress_count = len(active_projects)
        completed_count = len(completed_projects)
        pending_count = total_projects - in_progress_count - completed_count - len(blocked_projects)
        total_tasks = sum(p['count_tasks'] for p in projects_data)
        
        # Calcular tasas de completado por proyecto
        for project_data in projects_data:
            if project_data['count_tasks'] > 0:
                project_data['completion_rate'] = (project_data['completed_tasks'] / project_data['count_tasks']) * 100
            else:
                project_data['completion_rate'] = 0
        
        # Ordenar proyectos por tasa de completado (descendente)
        sorted_projects = sorted(projects_data, key=lambda x: x['completion_rate'], reverse=True)
        
        # Obtener proyectos activos para el dropdown de filtro
        active_projects_list = [p['project'] for p in active_projects]
        
        # Generar alertas comprehensivas
        alerts = generate_projects_overview_alerts(projects_data, request.user)
        
        # Añadir alertas de rendimiento
        performance_alerts = generate_performance_alerts(projects_data, request.user)
        alerts.extend(performance_alerts)
        
        # Añadir alertas específicas por proyecto
        for project_data in projects_data:
            if project_data['completion_rate'] > 90:
                alerts.append({
                    'type': 'success',
                    'icon': 'bi-trophy',
                    'title': f'¡Proyecto {project_data["project"].title} casi listo!',
                    'message': f'{project_data["completion_rate"]:.1f}% completado. ¿Listo para finalizar?',
                    'action_url': f'/events/projects/{project_data["project"].id}/',
                    'action_text': 'Ver proyecto'
                })
            elif project_data['completion_rate'] < 30:
                alerts.append({
                    'type': 'warning',
                    'icon': 'bi-exclamation-triangle',
                    'title': f'Proyecto {project_data["project"].title} con bajo progreso',
                    'message': f'Solo {project_data["completion_rate"]:.1f}% de las tareas completadas.',
                    'action_url': f'/events/projects/{project_data["project"].id}/',
                    'action_text': 'Revisar proyecto'
                })
        
        context = {
            'title': f'{title} (User Projects)',
            'event_statuses': statuses[0],
            'task_statuses': statuses[2],
            'project_statuses': statuses[1],
            'projects_data': sorted_projects,
            'active_projects': active_projects,
            'completed_projects': completed_projects,
            'blocked_projects': blocked_projects,
            'total_projects': total_projects,
            'in_progress_count': in_progress_count,
            'completed_count': completed_count,
            'pending_count': pending_count,
            'total_tasks': total_tasks,
            'active_projects_list': active_projects_list,
            'alerts': alerts,
            'is_single_project_view': False,
        }
        
        return render(request, 'projects/project_panel.html', context)
        
    except Exception as e:
        logger.error(f"Error en panel general de proyectos: {str(e)}", exc_info=True)
        messages.error(request, f'Ha ocurrido un error al cargar el panel de proyectos: {e}')
        
        # Contexto de fallback simple
        context = {
            'title': 'Project Panel',
            'projects_data': [],
            'alerts': [],
            'is_single_project_view': False,
        }
        return render(request, 'projects/project_panel.html', context)


# ============================================================================
# FUNCIONES DE ALERTAS PARA PROYECTOS
# ============================================================================

def generate_project_alerts(project_data, user):
    """
    Generate contextual alerts for a specific project
    """
    alerts = []
    project = project_data['project']
    tasks = project_data.get('tasks', [])

    # Alert: Project overdue
    if project.updated_at and (timezone.now() - project.updated_at).days > 7:
        alerts.append({
            'type': 'warning',
            'icon': 'bi-exclamation-triangle',
            'title': 'Proyecto inactivo',
            'message': f'El proyecto "{project.title}" no ha sido actualizado en {(timezone.now() - project.updated_at).days} días.',
            'action_url': f'/events/projects/edit/{project.id}',
            'action_text': 'Actualizar proyecto'
        })

    # Alert: Tasks completion status
    completed_tasks = project_data.get('completed_tasks', 0)
    total_tasks = project_data.get('total_tasks', 0)
    
    if total_tasks > 0:
        completion_rate = (completed_tasks / total_tasks) * 100
        if completion_rate < 30:
            alerts.append({
                'type': 'danger',
                'icon': 'bi-graph-down',
                'title': 'Bajo progreso',
                'message': f'Solo {completion_rate:.1f}% de las tareas completadas ({completed_tasks}/{total_tasks}).',
                'action_url': f'/events/tasks/?project_id={project.id}',
                'action_text': 'Ver tareas'
            })
        elif completion_rate > 90 and project.project_status.status_name != 'Completed':
            alerts.append({
                'type': 'success',
                'icon': 'bi-check-circle',
                'title': '¡Casi listo!',
                'message': f'{completion_rate:.1f}% de las tareas completadas. ¿Listo para finalizar?',
                'action_url': f'/events/projects/edit/{project.id}',
                'action_text': 'Marcar como completado'
            })

    # Alert: Multiple assignees
    if project.attendees.count() > 3:
        alerts.append({
            'type': 'info',
            'icon': 'bi-people',
            'title': 'Proyecto colaborativo',
            'message': f'{project.attendees.count()} personas trabajando en este proyecto.',
            'action_url': f'/events/projects/detail/{project.id}',
            'action_text': 'Ver detalles'
        })

    # Alert: High priority tasks
    high_priority_tasks = [task for task in tasks if task.important and task.task_status.status_name != 'Completed']
    if high_priority_tasks:
        alerts.append({
            'type': 'warning',
            'icon': 'bi-star-fill',
            'title': 'Tareas prioritarias',
            'message': f'{len(high_priority_tasks)} tarea(s) de alta prioridad pendiente(s).',
            'action_url': f'/events/tasks/?project_id={project.id}',
            'action_text': 'Revisar prioridades'
        })

    # Alert: Project blocked
    if project.project_status.status_name == 'Blocked':
        alerts.append({
            'type': 'danger',
            'icon': 'bi-slash-circle',
            'title': 'Proyecto bloqueado',
            'message': f'El proyecto "{project.title}" está bloqueado. Revisa las dependencias.',
            'action_url': f'/events/projects/edit/{project.id}',
            'action_text': 'Resolver bloqueo'
        })

    return alerts


def generate_projects_overview_alerts(projects_data, user):
    """
    Generate overview alerts for all projects
    """
    alerts = []

    if not projects_data:
        alerts.append({
            'type': 'info',
            'icon': 'bi-info-circle',
            'title': '¡Bienvenido!',
            'message': 'No tienes proyectos activos. ¿Quieres crear uno nuevo?',
            'action_url': '/events/projects/create/',
            'action_text': 'Crear proyecto'
        })
        return alerts

    # Alert: Overall completion rate
    total_tasks = sum(p['count_tasks'] for p in projects_data)
    completed_tasks = sum(p.get('completed_tasks', 0) for p in projects_data)

    if total_tasks > 0:
        overall_completion = (completed_tasks / total_tasks) * 100
        if overall_completion < 50:
            alerts.append({
                'type': 'warning',
                'icon': 'bi-bar-chart',
                'title': 'Progreso general bajo',
                'message': f'Solo {overall_completion:.1f}% de todas las tareas completadas.',
                'action_url': '/events/projects/',
                'action_text': 'Ver todos los proyectos'
            })
        elif overall_completion > 80:
            alerts.append({
                'type': 'success',
                'icon': 'bi-trophy',
                'title': '¡Excelente progreso!',
                'message': f'{overall_completion:.1f}% de todas las tareas completadas. ¡Sigue así!',
                'action_url': '/events/projects/',
                'action_text': 'Ver estadísticas'
            })

    # Alert: Projects without recent activity
    inactive_projects = []
    for p in projects_data:
        if p['project'].updated_at and (timezone.now() - p['project'].updated_at).days > 14:
            inactive_projects.append(p['project'])

    if inactive_projects:
        alerts.append({
            'type': 'danger',
            'icon': 'bi-clock',
            'title': 'Proyectos inactivos',
            'message': f'{len(inactive_projects)} proyecto(s) sin actividad reciente.',
            'action_url': '/events/projects/',
            'action_text': 'Revisar proyectos'
        })

    # Alert: High number of in-progress projects
    in_progress_projects = sum(1 for p in projects_data if p['project'].project_status.status_name == 'In Progress')
    if in_progress_projects > 5:
        alerts.append({
            'type': 'warning',
            'icon': 'bi-exclamation-circle',
            'title': 'Demasiados proyectos activos',
            'message': f'Tienes {in_progress_projects} proyectos en progreso. Considera priorizar.',
            'action_url': '/events/projects/',
            'action_text': 'Gestionar prioridades'
        })

    # Alert: Projects nearing completion
    nearly_complete = []
    for p in projects_data:
        count_tasks = p['count_tasks']
        if count_tasks > 0:
            completed_tasks = p.get('completed_tasks', 0)
            if completed_tasks / count_tasks > 0.8 and p['project'].project_status.status_name != 'Completed':
                nearly_complete.append(p['project'])

    if nearly_complete:
        alerts.append({
            'type': 'success',
            'icon': 'bi-trophy',
            'title': '¡Proyectos casi listos!',
            'message': f'{len(nearly_complete)} proyecto(s) están cerca de completarse.',
            'action_url': '/events/projects/',
            'action_text': 'Finalizar proyectos'
        })

    # Alert: Projects with many tasks
    overloaded_projects = []
    for p in projects_data:
        if p['count_tasks'] > 15:
            overloaded_projects.append(p['project'])

    if overloaded_projects:
        alerts.append({
            'type': 'warning',
            'icon': 'bi-list-check',
            'title': 'Proyectos sobrecargados',
            'message': f'{len(overloaded_projects)} proyecto(s) tienen más de 15 tareas.',
            'action_url': '/events/projects/',
            'action_text': 'Revisar distribución'
        })

    return alerts


def generate_performance_alerts(projects_data, user):
    """
    Generate performance-based alerts for projects
    """
    alerts = []

    # Calculate performance metrics
    total_projects = len(projects_data)
    if total_projects == 0:
        return alerts

    # Completion rate analysis
    completion_rates = []
    for p in projects_data:
        count_tasks = p['count_tasks']
        if count_tasks > 0:
            completed_tasks = p.get('completed_tasks', 0)
            rate = (completed_tasks / count_tasks) * 100
            completion_rates.append(rate)

    if completion_rates:
        avg_completion = sum(completion_rates) / len(completion_rates)

        if avg_completion < 25:
            alerts.append({
                'type': 'danger',
                'icon': 'bi-graph-down',
                'title': 'Rendimiento bajo',
                'message': f'El promedio de completación de proyectos es solo {avg_completion:.1f}%.',
                'action_url': '/events/projects/',
                'action_text': 'Mejorar rendimiento'
            })
        elif avg_completion > 75:
            alerts.append({
                'type': 'success',
                'icon': 'bi-graph-up',
                'title': '¡Excelente rendimiento!',
                'message': f'Promedio de completación del {avg_completion:.1f}%. ¡Sigue así!',
                'action_url': '/events/projects/',
                'action_text': 'Ver estadísticas'
            })

    # Task distribution analysis
    total_tasks = sum(p['count_tasks'] for p in projects_data)
    if total_tasks > 0:
        avg_tasks_per_project = total_tasks / total_projects

        if avg_tasks_per_project > 10:
            alerts.append({
                'type': 'warning',
                'icon': 'bi-list-check',
                'title': 'Proyectos complejos',
                'message': f'Promedio de {avg_tasks_per_project:.1f} tareas por proyecto. Considera dividir en proyectos más pequeños.',
                'action_url': '/events/projects/create/',
                'action_text': 'Crear subproyectos'
            })

    # Time-based analysis
    recent_projects = [p for p in projects_data if p['project'].created_at > timezone.now() - timezone.timedelta(days=7)]
    if recent_projects:
        alerts.append({
            'type': 'info',
            'icon': 'bi-calendar-plus',
            'title': 'Actividad reciente',
            'message': f'{len(recent_projects)} proyecto(s) creado(s) en la última semana.',
            'action_url': '/events/projects/',
            'action_text': 'Ver proyectos nuevos'
        })

    return alerts


# ============================================================================
# VISTAS PRINCIPALES DE PROYECTOS
# ============================================================================

@login_required
def projects(request, project_id=None):
    """
    Vista principal de proyectos - maneja listado y detalle
    """
    title = 'Projects'
    
    # URLs para navegación
    urls = [
        {'url_name': 'events:project_create', 'name': 'Project Create'},
    ]
    
    other_urls = [
        {'url_name': 'events:events', 'id': None, 'name': 'Events Panel'},
        {'url_name': 'events:projects', 'id': None, 'name': 'Projects Panel'},
        {'url_name': 'events:tasks', 'id': None, 'name': 'Tasks Panel'},
    ]
    
    instructions = [
        {'instruction': 'Fill carefully the metadata.', 'name': 'Form'},
    ]

    project_statuses = ProjectStatus.objects.all().order_by('status_name')

    # VISTA DETALLADA DE UN PROYECTO ESPECÍFICO
    if project_id:
        project = get_object_or_404(Project, id=project_id)
        
        # Obtener tareas del proyecto
        tasks = Task.objects.filter(project=project).select_related(
            'task_status', 'assigned_to'
        ).order_by('-created_at')
        
        # Calcular estadísticas del proyecto
        total_tasks = tasks.count()
        completed_tasks = tasks.filter(task_status__status_name='Completed').count()
        in_progress_tasks = tasks.filter(task_status__status_name='In Progress').count()
        pending_tasks = tasks.filter(task_status__status_name='To Do').count()
        
        project_data = {
            'project': project,
            'tasks': tasks,
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'in_progress_tasks': in_progress_tasks,
            'pending_tasks': pending_tasks,
        }
        
        # Generar alertas para el proyecto específico
        alerts = generate_project_alerts(project_data, request.user)
        
        return render(request, "projects/project_detail.html", {
            'title': title,
            'project': project,
            'project_data': project_data,
            'tasks': tasks,
            'alerts': alerts,
            'project_statuses': project_statuses,
        })

    # VISTA DE LISTADO DE PROYECTOS
    else:
        # Obtener proyectos del usuario
        projects_list = Project.objects.filter(
            Q(host=request.user) | Q(attendees=request.user)
        ).select_related(
            'project_status', 
            'event', 
            'host', 
            'assigned_to'
        ).prefetch_related(
            'attendees',
            'task_set'
        ).order_by('-created_at')
        
        # Preparar datos de proyectos con estadísticas
        projects_data = []
        for project in projects_list:
            # Contar tareas del proyecto
            count_tasks = project.task_set.count()
            
            # Obtener tareas del proyecto
            project_tasks = project.task_set.select_related('task_status').all()
            
            project_data = {
                'project': project,
                'count_tasks': count_tasks,
                'tasks': project_tasks,
            }
            
            projects_data.append(project_data)
        
        # Calcular estadísticas generales
        total_projects = len(projects_data)
        in_progress_count = sum(1 for p in projects_data 
                               if p['project'].project_status.status_name == 'In Progress')
        completed_count = sum(1 for p in projects_data 
                             if p['project'].project_status.status_name == 'Completed')
        total_tasks = sum(p['count_tasks'] for p in projects_data)
        
        # Generar alertas generales
        alerts = generate_projects_overview_alerts(projects_data, request.user)
        
        # Añadir alertas de rendimiento
        performance_alerts = generate_performance_alerts(projects_data, request.user)
        alerts.extend(performance_alerts)
        
        return render(request, "projects/projects.html", {
            'title': title,
            'projects': projects_list,
            'projects_data': projects_data,
            'alerts': alerts,
            'project_statuses': project_statuses,
            'total_projects': total_projects,
            'in_progress_count': in_progress_count,
            'completed_count': completed_count,
            'total_tasks': total_tasks,
        })


@login_required
def project_panel(request, project_id=None):
    """
    Vista principal del panel de proyectos - VERSIÓN COMPLETAMENTE OPTIMIZADA
    """
    title = "Project Panel"
    
    # Obtener estados del sistema
    statuses = statuses_get()
    
    # VISTA DETALLADA DE UN PROYECTO ESPECÍFICO
    if project_id:
        return render_single_project_view(
            request, project_id, title, statuses
        )
    
    # VISTA GENERAL DEL PANEL DE PROYECTOS (TODOS LOS PROYECTOS)
    return render_project_panel_view(
        request, title, statuses
    )


@login_required
def project_detail(request, project_id):
    """
    Vista detallada de un proyecto individual con estadísticas completas
    """
    project = get_object_or_404(Project, id=project_id)

    # Verificar permisos
    if not (project.host == request.user or request.user in project.attendees.all()):
        messages.error(request, 'No tienes permisos para ver este proyecto.')
        return redirect('events:projects')

    # Obtener tareas del proyecto con información detallada
    tasks = Task.objects.filter(project_id=project_id).select_related(
        'task_status', 'assigned_to', 'host'
    ).order_by('created_at')

    # Calcular estadísticas del proyecto
    total_tasks = tasks.count()
    completed_tasks = tasks.filter(task_status__status_name='Completed').count()
    in_progress_tasks = tasks.filter(task_status__status_name='In Progress').count()
    pending_tasks = tasks.filter(task_status__status_name='To Do').count()

    # Calcular progreso
    progress_percentage = 0
    if total_tasks > 0:
        progress_percentage = (completed_tasks / total_tasks) * 100

    # Tareas por estado para gráficos
    tasks_by_status = tasks.values('task_status__status_name').annotate(
        count=Count('id')
    ).order_by('task_status__status_name')

    # Tareas importantes
    important_tasks = tasks.filter(important=True).exclude(
        task_status__status_name='Completed'
    )

    # Actividad reciente (últimas 5 tareas actualizadas)
    recent_tasks = tasks.order_by('-updated_at')[:5]

    # Preparar datos del proyecto
    project_data = {
        'project': project,
        'tasks': tasks,
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'in_progress_tasks': in_progress_tasks,
        'pending_tasks': pending_tasks,
        'progress_percentage': progress_percentage,
        'important_tasks_count': important_tasks.count(),
    }

    # Generar alertas
    alerts = generate_project_alerts(project_data, request.user)

    context = {
        'project': project,
        'project_data': project_data,
        'tasks': tasks,
        
        # Estadísticas
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'in_progress_tasks': in_progress_tasks,
        'pending_tasks': pending_tasks,
        'progress_percentage': progress_percentage,
        'important_tasks_count': important_tasks.count(),

        # Datos para gráficos
        'tasks_by_status': tasks_by_status,

        # Actividad
        'recent_tasks': recent_tasks,
        'important_tasks': important_tasks,

        # Alertas
        'alerts': alerts,
    }

    return render(request, 'projects/project_detail.html', context)


# ============================================================================
# VISTAS CRUD DE PROYECTOS
# ============================================================================

@login_required
def project_create(request):
    """
    Vista para crear un nuevo proyecto usando ProjectManager para consistencia
    """
    urls = [
        {'url_name': 'events:project_create', 'name': 'Project Create'},
    ]
    
    other_urls = [
        {'url_name': 'events:events', 'id': None, 'name': 'Events Panel'},
        {'url_name': 'events:projects', 'id': None, 'name': 'Projects Panel'},
        {'url_name': 'events:tasks', 'id': None, 'name': 'Tasks Panel'},
    ]
    
    title = "Create New Project"
    
    if request.method == 'GET':
        form = CreateNewProject()
    else:
        form = CreateNewProject(request.POST)

        if form.is_valid():
            try:
                # Usar ProjectManager para consistencia
                project_manager = ProjectManager(request.user)
                
                # Preparar datos del formulario
                title = form.cleaned_data['title']
                description = form.cleaned_data.get('description', '')
                assigned_to = form.cleaned_data.get('assigned_to', request.user)
                event = form.cleaned_data.get('event')
                
                # Crear proyecto usando ProjectManager
                project = project_manager.create_project(
                    title=title,
                    description=description,
                    project_status=None,  # Usará 'Created' por defecto
                    assigned_to=assigned_to,
                    ticket_price=0.07,
                    event=event
                )
                
                # Agregar asistentes si existen
                attendees = form.cleaned_data.get('attendees', [])
                if attendees:
                    project.attendees.set(attendees)
                
                messages.success(request, 'Proyecto creado exitosamente!')
                return redirect('events:project_panel')
                
            except Exception as e:
                messages.error(request, f'Error al crear el proyecto: {e}')
        else:
            messages.error(request, 'Por favor, corrige los errores en el formulario.')

    return render(request, 'projects/project_create.html', {
        'form': form,
        'title': title,
        'urls': urls,
        'other_urls': other_urls,
    })

@login_required
def project_edit(request, project_id=None):
    """
    Vista para editar un proyecto existente o listar proyectos
    """
    try:
        if project_id is not None:
            title = "Project Edit"

            # Estamos editando un proyecto existente
            try:
                project = get_object_or_404(Project, pk=project_id)
            except Http404:
                messages.error(request, 'El proyecto con el ID "{}" no existe.'.format(project_id))
                return redirect('home')

            # Verificar permisos - solo el host o attendees pueden editar
            if not (project.host == request.user or request.user in project.attendees.all()):
                messages.error(request, 'No tienes permisos para editar este proyecto.')
                return redirect('events:projects')

            if request.method == 'POST':
                form = CreateNewProject(request.POST, instance=project)
                if form.is_valid():
                    # Asigna el usuario autenticado como el editor
                    project.editor = request.user

                    # Guardar el proyecto con el editor actual
                    for field in form.changed_data:
                        old_value = getattr(project, field)
                        new_value = form.cleaned_data.get(field)
                        project.record_edit(
                            editor=request.user,
                            field_name=field,
                            old_value=str(old_value),
                            new_value=str(new_value)
                        )
                    form.save()

                    messages.success(request, 'Proyecto guardado con éxito.')
                    return redirect('events:projects')  # Redirige a la página de lista de edición
                else:
                    messages.error(request, 'Hubo un error al guardar el proyecto. Por favor, revisa el formulario.')
            else:
                form = CreateNewProject(instance=project)
            
            return render(request, 'projects/project_edit.html', {
                'form': form,
                'title': title,
            })
        
        else:
            title = "Projects list"

            # Estamos manejando una solicitud GET sin argumentos
            # Verificar el rol del usuario
            if request.user.is_superuser or (hasattr(request.user, 'cv') and getattr(request.user.cv, 'role', None) == 'SU'):
                # Si el usuario es un 'SU', puede ver todos los proyectos
                projects = Project.objects.all().order_by('-updated_at')
            else:
                # Si no, solo puede ver los proyectos que le están asignados o a los que asiste
                projects = Project.objects.filter(Q(assigned_to=request.user) | Q(attendees=request.user)).distinct().order_by('-updated_at')
            
            return render(request, 'projects/project_list.html', {
                'projects': projects,
                'title': title,
            })
    
    except Exception as e:
        messages.error(request, 'Ha ocurrido un error: {}'.format(e))
        return redirect('home')


@login_required
def project_delete(request, project_id):
    """
    Vista para eliminar un proyecto
    """
    if request.method == 'POST':
        project = get_object_or_404(Project, pk=project_id)

        # Verificar permisos - solo el host o attendees pueden eliminar
        if not (project.host == request.user or request.user in project.attendees.all()):
            messages.error(request, 'No tienes permiso para eliminar este proyecto.')
            return redirect('events:project_panel')

        project.delete()
        messages.success(request, 'El proyecto ha sido eliminado exitosamente.')
    else:
        messages.error(request, 'Método no permitido.')
    
    return redirect('events:project_panel')


# ============================================================================
# OPERACIONES DE ESTADO Y ACCIONES MASIVAS
# ============================================================================

@login_required
def change_project_status(request, project_id):
    """
    Cambiar el estado de un proyecto
    """
    try:
        if request.method != 'POST':
            return HttpResponse("Método no permitido", status=405)
        
        project = get_object_or_404(Project, pk=project_id)
        new_status_id = request.POST.get('new_status_id')
        new_status = get_object_or_404(ProjectStatus, pk=new_status_id)
        
        if request.user is None:
            messages.error(request, "User is none: Usuario no autenticado")
            return redirect('home')
        
        if project.host is not None and (project.host == request.user or request.user in project.attendees.all()):
            old_status = project.project_status
            project.record_edit(
                editor=request.user,
                field_name='project_status',
                old_value=str(old_status),
                new_value=str(new_status)
            )
        else:
            return HttpResponse("No tienes permiso para editar este proyecto", status=403)
        
    except Exception as e:
        return HttpResponse(f"Error: {str(e)}", status=500)
    
    messages.success(request, 'Project status edited successfully!')
    return redirect('events:project_panel')


@login_required
def project_activate(request, project_id=None):
    """
    Vista para activar un proyecto o listar proyectos para activación
    """
    title = 'Project Activate'
    
    if project_id:
        project = get_object_or_404(Project, pk=project_id)
        try:
            active_status = ProjectStatus.objects.get(status_name='In Progress')
            project.project_status = active_status
            project.save()
            messages.success(request, 'El proyecto ha sido activado exitosamente.')
        except ProjectStatus.DoesNotExist:
            messages.error(request, 'El estado "Activo" no existe en la base de datos.')
        except Exception as e:
            messages.error(request, f'Ocurrió un error al intentar activar el proyecto: {e}')
        
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
    
    else:
        projects = Project.objects.all().order_by('-updated_at')
        # Crea una lista para almacenar los proyectos y sus recuentos de tareas
        projects_with_task_count = []
        
        for project in projects:
            # Cuenta las tareas para el proyecto actual
            count_tasks = Task.objects.filter(project_id=project.id).count()
            # Almacena el proyecto y su recuento de tareas en la lista
            projects_with_task_count.append((project, count_tasks))
        
        try:
            return render(request, "projects/project_activate.html", {
                'title': f'{title} (No iD)',
                'projects_with_task_count': projects_with_task_count,
            })
        except Exception as e:
            messages.error(request, 'Ha ocurrido un error: {}'.format(e))
            return redirect('events:project_panel')


@login_required
def project_bulk_action(request):
    """
    Vista para acciones masivas en proyectos
    """
    if request.method == 'POST':
        action = request.POST.get('action')
        selected_projects = request.POST.getlist('selected_projects')

        if not selected_projects:
            messages.error(request, 'No se seleccionaron proyectos.')
            return redirect('events:project_panel')

        projects = Project.objects.filter(id__in=selected_projects)

        if action == 'delete':
            if not (request.user.is_superuser or (hasattr(request.user, 'cv') and getattr(request.user.cv, 'role', None) == 'SU')):
                messages.error(request, 'No tienes permiso para eliminar proyectos.')
                return redirect('events:project_panel')

            count = projects.count()
            projects.delete()
            messages.success(request, f'Se eliminaron {count} proyecto(s) exitosamente.')

        elif action == 'activate':
            active_status = ProjectStatus.objects.get(status_name='In Progress')
            count = projects.update(project_status=active_status)
            messages.success(request, f'Se activaron {count} proyecto(s) exitosamente.')

        elif action == 'complete':
            completed_status = ProjectStatus.objects.get(status_name='Completed')
            count = projects.update(project_status=completed_status)
            messages.success(request, f'Se completaron {count} proyecto(s) exitosamente.')

        else:
            messages.error(request, 'Acción no válida.')

    return redirect('events:project_panel')


@login_required
def project_export(request):
    """
    Vista para exportar proyectos a CSV
    """
    if request.method == 'POST':
        selected_projects = request.POST.getlist('selected_projects')
        if selected_projects:
            projects = Project.objects.filter(id__in=selected_projects)
        else:
            projects = Project.objects.all()
    else:
        projects = Project.objects.all()

    # Crear respuesta CSV
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="projects_export.csv"'

    writer = csv.writer(response)
    writer.writerow(['ID', 'Title', 'Description', 'Status', 'Event', 'Host', 'Created At', 'Updated At'])

    for project in projects:
        writer.writerow([
            project.id,
            project.title,
            project.description or '',
            project.project_status.status_name,
            project.event.title if project.event else 'None',
            project.host.username,
            project.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            project.updated_at.strftime('%Y-%m-%d %H:%M:%S')
        ])

    return response


# ============================================================================
# VISTAS AJAX/API
# ============================================================================

@login_required
def get_project_alerts_ajax(request):
    """
    AJAX endpoint to get project alerts
    """
    if request.method == 'GET' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            project_manager = ProjectManager(request.user)
            projects, _ = project_manager.get_all_projects()

            alerts = generate_projects_overview_alerts(projects, request.user)
            performance_alerts = generate_performance_alerts(projects, request.user)
            alerts.extend(performance_alerts)

            return JsonResponse({
                'success': True,
                'alerts': alerts,
                'count': len(alerts)
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })

    return JsonResponse({
        'success': False,
        'error': 'Invalid request'
    })
    
def project_tasks_status_check(request, project_id):
    task_active_status = TaskStatus.objects.filter(status_name='In Progress').first()
    task_finished_status = TaskStatus.objects.filter(status_name='Completed').first()
    project_active_status = ProjectStatus.objects.filter(status_name='In Progress').first()
    project_finished_status = ProjectStatus.objects.filter(status_name='Completed').first()

    if not task_active_status or not task_finished_status or not project_active_status or not project_finished_status:
        return render(request, 'projects/projects_check.html', {
            'error': 'Statuses not found'
        })

    project = get_object_or_404(Project, id=project_id)
    project_tasks = Task.objects.filter(project_id=project.id)
    active_tasks = project_tasks.filter(task_status=task_active_status)

    if active_tasks.exists():
        # Preguntar al usuario si desea forzar el cierre de las tareas activas
        if request.method == 'POST' and 'force_close' in request.POST:
            # Forzar el cierre de todas las tareas activas
            for task in active_tasks:
                old_status = task.task_status
                task.record_edit(
                    editor=request.user,
                    field_name='task_status',
                    old_value=str(old_status),
                    new_value=str(task_finished_status)
                )
                # Ejecutar event.record_edit para el evento de cada tarea
                if hasattr(task, 'event'):
                    print('have event')
                    event = task.event
                    event_old_status = event.event_status  # Suponiendo que 'status' es el campo relevante en el evento
                    event.record_edit(
                        editor=request.user,
                        field_name='event_status',
                        old_value=str(event_old_status),
                        new_value=str(task_finished_status)  # O el estado que corresponda para el evento
                    )
                else:
                    print('doesnt have event')

            # Actualizar el estado del proyecto a Completed
            old_status = project.project_status
            project.record_edit(
                editor=request.user,
                field_name='project_status',
                old_value=str(old_status),
                new_value=str(project_finished_status)
            )
        else:
            # Renderizar una plantilla que pregunte al usuario si desea forzar el cierre
            return render(request, 'projects/confirm_force_close.html', {
                'project': project,
                'active_tasks': active_tasks
            })

    return render(request, 'projects/projects_check.html', {
        'project_tasks': project_tasks
    })
