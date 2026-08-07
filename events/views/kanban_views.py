# events/kanban_views.py
# ============================================================================
# VISTAS KANBAN PARA TABLEROS DE TAREAS Y PROYECTOS
# ============================================================================

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import redirect, render, get_object_or_404

from ..models import Project, Task, TagCategory, InboxItem, TaskStatus
from ..management.task_manager import TaskManager
from ..management.project_manager import ProjectManager
from ..management.event_manager import EventManager

# ============================================================================
# VISTAS KANBAN PRINCIPALES
# ============================================================================

@login_required
def kanban_board_unified(request):
    """
    Vista Kanban unificada que integra las mejores características de ambas vistas
    """
    title = "Panel Kanban Unificado"

    # Obtener todas las tareas del usuario
    task_manager = TaskManager(request.user)
    tasks_data, _ = task_manager.get_all_tasks()

    # Obtener proyectos del usuario
    project_manager = ProjectManager(request.user)
    projects_data, _ = project_manager.get_all_projects()

    # Obtener eventos del usuario
    event_manager = EventManager(request.user)
    events_data, _ = event_manager.get_all_events()

    # Organizar tareas por estado para el kanban principal
    statuses = TaskStatus.objects.all()
    status_map = {status.status_name: status for status in statuses}
    kanban_columns = {}
    for status_name, column_data in {
        'To Do': {
            'title': 'Por Hacer',
            'color': '#6c757d',
            'tasks': []
        },
        'In Progress': {
            'title': 'En Progreso',
            'color': '#007bff',
            'tasks': []
        },
        'Completed': {
            'title': 'Completado',
            'color': '#28a745',
            'tasks': []
        },
        'In Review': {
            'title': 'En Revisión',
            'color': '#fd7e14',
            'tasks': []
        }
    }.items():
        status_obj = status_map.get(status_name)
        column_data['status_id'] = status_obj.id if status_obj else None
        column_data['status_name'] = status_name
        kanban_columns[status_name] = column_data

    # Categorizar las tareas
    for task_data in tasks_data:
        task = task_data['task']
        status_name = task.task_status.status_name

        if status_name in kanban_columns:
            kanban_columns[status_name]['tasks'].append(task_data)

    # Secciones adicionales organizadas (versión mejorada)
    organized_sections = {
        'recent_projects': {
            'title': 'Proyectos Recientes',
            'icon': 'bi-folder',
            'color': 'primary',
            'items': projects_data[:5],
            'view_all_url': 'events:projects'
        },
        'active_events': {
            'title': 'Eventos Activos',
            'icon': 'bi-calendar-event',
            'color': 'success',
            'items': [e for e in events_data if e['event'].event_status.status_name == 'In Progress'][:5],
            'view_all_url': 'events:events'
        },
        'gtd_tools': {
            'title': 'Herramientas GTD',
            'icon': 'bi-lightbulb',
            'color': 'warning',
            'items': [
                {'name': 'Bandeja de Entrada', 'url': 'events:inbox', 'icon': 'bi-inbox', 'description': 'Capturar tareas rápidamente'},
                {'name': 'Matriz Eisenhower', 'url': 'events:eisenhower_matrix', 'icon': 'bi-grid-3x3', 'description': 'Priorizar tareas'},
                {'name': 'Dependencias', 'url': 'events:task_dependencies_list', 'icon': 'bi-link', 'description': 'Gestionar dependencias'},
                {'name': 'Plantillas', 'url': 'events:project_templates', 'icon': 'bi-file-earmark-plus', 'description': 'Crear desde plantillas'},
            ],
            'view_all_url': None
        },
        'quick_config': {
            'title': 'Configuración Rápida',
            'icon': 'bi-gear',
            'color': 'info',
            'items': [
                {'name': 'Crear Tarea', 'url': 'events:task_create', 'icon': 'bi-plus-circle', 'description': 'Nueva tarea rápida'},
                {'name': 'Crear Proyecto', 'url': 'events:project_create', 'icon': 'bi-folder-plus', 'description': 'Nuevo proyecto'},
                {'name': 'Crear Evento', 'url': 'events:event_create', 'icon': 'bi-calendar-plus', 'description': 'Nuevo evento'},
                {'name': 'Recordatorios', 'url': 'events:reminders_dashboard', 'icon': 'bi-bell', 'description': 'Gestionar recordatorios'},
            ],
            'view_all_url': 'events:status'
        }
    }

    # Obtener etiquetas disponibles para filtros
    tag_categories = TagCategory.objects.filter(is_system=True)

    # Calcular estadísticas generales mejoradas
    total_tasks = len(tasks_data)
    in_progress_count = sum(1 for task_data in tasks_data if task_data['task'].task_status.status_name == 'In Progress')
    completed_count = sum(1 for task_data in tasks_data if task_data['task'].task_status.status_name == 'Completed')
    pending_count = sum(1 for task_data in tasks_data if task_data['task'].task_status.status_name == 'To Do')

    # Estadísticas de tareas para el template
    task_stats = {
        'completed': completed_count,
        'in_progress': in_progress_count,
        'pending': pending_count,
    }

    # Estadísticas de proyectos
    total_projects = len(projects_data)
    active_projects = [p for p in projects_data if p['project'].project_status.status_name == 'In Progress']

    # Estadísticas de eventos
    total_events = len(events_data)
    active_events = [e for e in events_data if e['event'].event_status.status_name == 'In Progress']

    # Items del inbox GTD para mostrar en el panel
    inbox_items = InboxItem.objects.filter(created_by=request.user, is_processed=False)[:5]

    # Obtener proyectos para el modal de creación rápida (de la primera vista)
    projects = Project.objects.filter(
        Q(host=request.user) | Q(attendees=request.user)
    ).distinct().order_by('-updated_at')

    context = {
        'title': title,
        'kanban_columns': kanban_columns,
        'organized_sections': organized_sections,
        'tag_categories': tag_categories,

        # Estadísticas
        'total_tasks': total_tasks,
        'in_progress_count': in_progress_count,
        'completed_count': completed_count,
        'pending_count': pending_count,
        'task_stats': task_stats,
        'total_projects': total_projects,
        'active_projects': active_projects,
        'total_events': total_events,
        'active_events': active_events,

        # Datos adicionales de ambas vistas
        'inbox_items': inbox_items,
        'projects': projects,  # Para el modal de creación rápida
        'recent_projects': projects[:5],  # Para la sección de proyectos recientes
        'recent_activities': [],  # Podría implementarse más tarde
    }

    return render(request, 'events/kanban_enhanced.html', context)


@login_required
def kanban_project(request, project_id):
    """
    Vista Kanban específica para un proyecto
    """
    title = "Kanban del Proyecto"

    try:
        project = Project.objects.get(id=project_id)
        if not (project.host == request.user or request.user in project.attendees.all()):
            messages.error(request, 'No tienes permisos para ver este proyecto.')
            return redirect('events:projects')
    except Project.DoesNotExist:
        messages.error(request, 'El proyecto no existe.')
        return redirect('events:projects')

    # Obtener tareas del proyecto específico
    tasks = Task.objects.filter(project=project).select_related(
        'task_status', 'assigned_to', 'host'
    )

    # Organizar tareas por estado
    kanban_columns = {
        'To Do': {
            'title': 'Por Hacer',
            'color': '#6c757d',
            'tasks': []
        },
        'In Progress': {
            'title': 'En Progreso',
            'color': '#007bff',
            'tasks': []
        },
        'In Review': {
            'title': 'En Revisión',
            'color': '#fd7e14',
            'tasks': []
        },
        'Completed': {
            'title': 'Completado',
            'color': '#28a745',
            'tasks': []
        }
    }

    # Categorizar las tareas
    for task in tasks:
        status_name = task.task_status.status_name
        if status_name in kanban_columns:
            # Obtener etiquetas de la tarea
            task_tags = task.tags.all()  # Las tareas pueden tener etiquetas a través del modelo Tag

            task_data = {
                'task': task,
                'tags': task_tags
            }
            kanban_columns[status_name]['tasks'].append(task_data)

    # Obtener etiquetas disponibles para filtros
    tag_categories = TagCategory.objects.filter(is_system=True)

    context = {
        'title': title,
        'project': project,
        'kanban_columns': kanban_columns,
        'tag_categories': tag_categories,
    }

    return render(request, 'events/kanban_enhanced.html', context)