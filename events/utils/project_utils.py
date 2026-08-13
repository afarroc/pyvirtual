"""
Utilidades de Proyectos (Project Utilities)
Centraliza la lógica de creación, gestión y alertas de proyectos en toda la aplicación
Proporciona funciones consistentes para el ciclo de vida completo de proyectos
"""

import logging
from django.utils import timezone
from django.db.models import Q

from ..models import Status, Event
from ..management.project_manager import ProjectManager
from .status_utils import get_default_status

logger = logging.getLogger(__name__)


# ============================================================================
# CREACIÓN CONSISTENTE DE PROYECTOS
# ============================================================================

def create_consistent_project(user, title, description='', assigned_to=None, 
                            event=None, attendees=None, **kwargs):
    """
    Función helper para crear proyectos consistentemente en toda la aplicación
    
    Args:
        user (User): Usuario creador
        title (str): Título del proyecto
        description (str): Descripción
        assigned_to (User, optional): Usuario asignado
        event (Event, optional): Evento asociado
        attendees (list, optional): Lista de asistentes
        **kwargs: Parámetros adicionales
        
    Returns:
        tuple: (project, event)
        
    Raises:
        Exception: Si hay error en la creación
    """
    logger.info(f"Creating consistent project '{title}' for user {user.username}")
    
    project_manager = ProjectManager(user)
    
    # Si no se especifica assigned_to, usar al usuario
    if assigned_to is None:
        assigned_to = user
        logger.debug(f"Using user {user.username} as assigned_to")
    
    # Si no hay evento, NO crear uno por defecto.
    # El campo `event` en Project/Task es opcional y solo se asigna
    # cuando el flujo de creación lo solicita explícitamente.
    if event is None:
        logger.debug("No event provided, leaving event=None")
    else:
        logger.debug(f"Using provided event (ID: {event.id})")
    
    # Crear proyecto usando ProjectManager
    project = project_manager.create_project(
        title=title,
        description=description,
        assigned_to=assigned_to,
        event=event,
        **kwargs
    )
    
    # Agregar asistentes si se especifican
    if attendees:
        project.attendees.set(attendees)
        logger.debug(f"Added {len(attendees)} attendees to project")
    
    logger.info(f"Project '{title}' created successfully (ID: {project.id})")
    return project, event


# ============================================================================
# GENERADOR DE ALERTAS DE PROYECTOS
# ============================================================================

def get_project_alerts(project_data, user):
    """
    Generar alertas para proyectos basadas en múltiples criterios:
    - Tareas vencidas
    - Tareas próximas a vencer
    - Proyectos sin tareas
    - Proyectos estancados
    - Progreso lento
    - Exceso de tareas sin asignar
    """
    from ..models import TaskStatus
    
    alerts = []
    project = project_data['project']
    tasks = project_data.get('tasks', [])
    
    if not project:
        return alerts
    
    today = timezone.now().date()
    
    # ------------------------------------------------------------------------
    # ALERTA 1: Tareas vencidas
    # ------------------------------------------------------------------------
    overdue_tasks = []
    for task in tasks:
        if hasattr(task, 'due_date') and task.due_date and task.due_date < today:
            status_name = task.task_status.status_name if task.task_status else 'Unknown'
            if status_name not in ['Completed', 'Cancelled']:
                overdue_tasks.append(task)
    
    if overdue_tasks:
        alerts.append({
            'level': 'danger',
            'icon': 'exclamation-triangle',
            'title': f'Tareas vencidas ({len(overdue_tasks)})',
            'message': f'El proyecto tiene {len(overdue_tasks)} tareas vencidas sin completar.',
            'tasks': overdue_tasks[:5]
        })
    
    # ------------------------------------------------------------------------
    # ALERTA 2: Tareas próximas a vencer (próximos 3 días)
    # ------------------------------------------------------------------------
    upcoming_tasks = []
    for task in tasks:
        if hasattr(task, 'due_date') and task.due_date:
            days_until_due = (task.due_date - today).days
            if 0 <= days_until_due <= 3:
                status_name = task.task_status.status_name if task.task_status else 'Unknown'
                if status_name not in ['Completed', 'Cancelled']:
                    upcoming_tasks.append(task)
    
    if upcoming_tasks:
        alerts.append({
            'level': 'warning',
            'icon': 'clock',
            'title': f'Tareas por vencer ({len(upcoming_tasks)})',
            'message': f'{len(upcoming_tasks)} tareas vencen en los próximos 3 días.',
            'tasks': upcoming_tasks[:5]
        })
    
    # ------------------------------------------------------------------------
    # ALERTA 3: Proyecto sin tareas
    # ------------------------------------------------------------------------
    if len(tasks) == 0:
        alerts.append({
            'level': 'info',
            'icon': 'info-circle',
            'title': 'Proyecto sin tareas',
            'message': 'Este proyecto no tiene tareas asignadas. Considere crear tareas para definir el trabajo pendiente.',
            'action_url': f'/tasks/create/?project={project.id}',
            'action_text': 'Crear tarea'
        })
    
    # ------------------------------------------------------------------------
    # ALERTA 4: Proyecto estancado (sin actualizaciones > 14 días)
    # ------------------------------------------------------------------------
    days_since_update = (today - project.updated_at.date()).days
    if days_since_update > 14 and project.project_status.status_name not in ['Completed', 'Cancelled']:
        alerts.append({
            'level': 'warning',
            'icon': 'pause-circle',
            'title': 'Proyecto estancado',
            'message': f'Este proyecto no ha sido actualizado en {days_since_update} días.',
            'days': days_since_update
        })
    
    # ------------------------------------------------------------------------
    # ALERTA 5: Progreso lento (menos del 30% completado y creado hace > 30 días)
    # ------------------------------------------------------------------------
    if hasattr(project, 'created_at'):
        days_since_creation = (today - project.created_at.date()).days
        if days_since_creation > 30:
            total_tasks = len(tasks)
            completed_tasks = 0
            
            if total_tasks > 0:
                for task in tasks:
                    if hasattr(task, 'task_status') and task.task_status:
                        if task.task_status.status_name == 'Completed':
                            completed_tasks += 1
                
                completion_percentage = (completed_tasks / total_tasks) * 100
                
                if completion_percentage < 30:
                    alerts.append({
                        'level': 'warning',
                        'icon': 'turtle',
                        'title': 'Progreso lento',
                        'message': f'Solo {completion_percentage:.1f}% completado después de {days_since_creation} días.',
                        'percentage': completion_percentage,
                        'days': days_since_creation
                    })
    
    # ------------------------------------------------------------------------
    # ALERTA 6: Exceso de tareas sin asignar
    # ------------------------------------------------------------------------
    unassigned_tasks = [task for task in tasks if not task.assigned_to]
    if len(unassigned_tasks) > 3:
        alerts.append({
            'level': 'info',
            'icon': 'user-slash',
            'title': f'Tareas sin asignar ({len(unassigned_tasks)})',
            'message': f'Hay {len(unassigned_tasks)} tareas sin responsable asignado.',
            'unassigned_count': len(unassigned_tasks)
        })
    
    logger.debug(f"Generated {len(alerts)} alerts for project {project.id}")
    return alerts