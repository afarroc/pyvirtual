"""
Utilidades GTD (Getting Things Done)
Centraliza funciones para el sistema de inbox y procesamiento
"""

import logging
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils import timezone
from ..models import InboxItem, Task, Project, Event
from .status_utils import get_default_status
from .managers import get_managers_for_user

logger = logging.getLogger(__name__)


def verify_inbox_links():
    """
    Verifica todos los enlaces de items procesados y reporta problemas
    
    Returns:
        list: Lista de problemas encontrados
    """
    issues = []
    processed_items = InboxItem.objects.filter(is_processed=True)
    
    logger.info(f"Verifying links for {processed_items.count()} processed inbox items")
    
    for item in processed_items:
        try:
            # Verificar si tiene enlace
            if not item.processed_to_content_type or not item.processed_to_object_id:
                issues.append({
                    'item_id': item.id,
                    'item_title': item.title,
                    'issue': 'Falta información de enlace',
                    'action_needed': 'Revisar manualmente',
                    'severity': 'high'
                })
                continue
            
            # Intentar acceder al objeto
            linked_object = item.processed_to
            
            if linked_object is None:
                issues.append({
                    'item_id': item.id,
                    'item_title': item.title,
                    'issue': 'Objeto enlazado no encontrado',
                    'content_type': str(item.processed_to_content_type),
                    'object_id': item.processed_to_object_id,
                    'action_needed': 'Buscar objeto alternativo o eliminar enlace',
                    'severity': 'high'
                })
            
        except Exception as e:
            issues.append({
                'item_id': item.id,
                'item_title': item.title,
                'issue': f'Error al acceder al objeto: {str(e)}',
                'action_needed': 'Corregir manualmente',
                'severity': 'medium'
            })
    
    logger.info(f"Link verification complete. Found {len(issues)} issues.")
    return issues


def fix_broken_links():
    """
    Intenta corregir enlaces rotos automáticamente
    
    Returns:
        dict: Estadísticas de corrección
    """
    fixed = 0
    failed = 0
    
    # Obtener content types
    task_content_type = ContentType.objects.get_for_model(Task)
    project_content_type = ContentType.objects.get_for_model(Project)
    event_content_type = ContentType.objects.get_for_model(Event)
    
    # Verificar enlaces a tareas
    task_items = InboxItem.objects.filter(
        processed_to_content_type=task_content_type,
        is_processed=True
    )
    
    logger.info(f"Attempting to fix links for {task_items.count()} task-linked items")
    
    for item in task_items:
        try:
            task = item.processed_to
            if task is None:
                # Intentar encontrar una tarea similar
                similar_tasks = Task.objects.filter(
                    title__icontains=item.title
                )[:1]
                
                if similar_tasks.exists():
                    similar_task = similar_tasks.first()
                    if _fix_link_safe(item, similar_task):
                        logger.info(f"Link fixed: Item {item.id} -> Task {similar_task.id}")
                        fixed += 1
                    else:
                        failed += 1
                else:
                    # Buscar en proyectos relacionados
                    similar_projects = Project.objects.filter(
                        title__icontains=item.title
                    )[:1]
                    
                    if similar_projects.exists():
                        similar_project = similar_projects.first()
                        if _fix_link_safe(item, similar_project):
                            logger.info(f"Link fixed: Item {item.id} -> Project {similar_project.id}")
                            fixed += 1
                        else:
                            failed += 1
                    else:
                        failed += 1
        except Exception as e:
            logger.error(f"Error processing item {item.id}: {e}")
            failed += 1
    
    result = {
        'fixed': fixed,
        'failed': failed,
        'total_checked': task_items.count()
    }
    
    logger.info(f"Link fixing complete. Fixed: {fixed}, Failed: {failed}")
    return result


def _fix_link_safe(item, target_object):
    """
    Versión segura de fix_link con manejo de errores
    
    Args:
        item (InboxItem): Item a corregir
        target_object: Objeto destino
        
    Returns:
        bool: True si se corrigió exitosamente
    """
    try:
        with transaction.atomic():
            item.processed_to_content_type = ContentType.objects.get_for_model(target_object)
            item.processed_to_object_id = target_object.id
            item.save(update_fields=['processed_to_content_type', 'processed_to_object_id'])
            return True
    except Exception as e:
        logger.error(f"Error fixing link for item {item.id}: {e}")
        return False


def get_inbox_statistics():
    """
    Obtiene estadísticas del sistema de inbox
    
    Returns:
        dict: Estadísticas de inbox
    """
    total_items = InboxItem.objects.count()
    processed_items = InboxItem.objects.filter(is_processed=True).count()
    unprocessed_items = InboxItem.objects.filter(is_processed=False).count()
    
    # Por tipo de contenido
    task_items = InboxItem.objects.filter(
        processed_to_content_type=ContentType.objects.get_for_model(Task)
    ).count()
    
    project_items = InboxItem.objects.filter(
        processed_to_content_type=ContentType.objects.get_for_model(Project)
    ).count()
    
    event_items = InboxItem.objects.filter(
        processed_to_content_type=ContentType.objects.get_for_model(Event)
    ).count()
    
    # Items sin clasificar
    unclassified = InboxItem.objects.filter(
        is_processed=True,
        processed_to_content_type__isnull=True
    ).count()
    
    # Items con problemas
    broken_links = len(verify_inbox_links())
    
    return {
        'total': total_items,
        'processed': processed_items,
        'unprocessed': unprocessed_items,
        'processing_rate': round((processed_items / total_items * 100) if total_items > 0 else 0, 1),
        'by_type': {
            'tasks': task_items,
            'projects': project_items,
            'events': event_items,
            'unclassified': unclassified
        },
        'issues': {
            'broken_links': broken_links
        }
    }


def classify_inbox_item(item_id, target_type, target_id=None, user=None):
    """
    Clasifica un item de inbox creando el objeto correspondiente
    
    Args:
        item_id (int): ID del item de inbox
        target_type (str): Tipo de destino ('task', 'project', 'event')
        target_id (int, optional): ID del objeto existente
        user (User, optional): Usuario que realiza la clasificación
        
    Returns:
        tuple: (success, message, object_created)
    """
    try:
        item = InboxItem.objects.get(id=item_id)
        
        if item.is_processed:
            return False, "Este item ya ha sido procesado", None
        
        with transaction.atomic():
            # Si se proporciona un ID existente, asignar a ese objeto
            if target_id:
                return _assign_to_existing(item, target_type, target_id, user)
            else:
                # Crear nuevo objeto
                return _create_from_inbox(item, target_type, user)
                
    except InboxItem.DoesNotExist:
        return False, f"Item {item_id} no encontrado", None
    except Exception as e:
        logger.exception(f"Error classifying inbox item {item_id}: {e}")
        return False, f"Error al clasificar: {str(e)}", None


def _assign_to_existing(item, target_type, target_id, user):
    """
    Asigna un item de inbox a un objeto existente
    """
    model_map = {
        'task': Task,
        'project': Project,
        'event': Event
    }
    
    model = model_map.get(target_type)
    if not model:
        return False, f"Tipo inválido: {target_type}", None
    
    try:
        target_object = model.objects.get(id=target_id)
        
        # Actualizar item
        item.is_processed = True
        item.processed_to = target_object
        item.processed_at = timezone.now()
        item.processed_by = user
        item.save()
        
        logger.info(f"Inbox item {item.id} assigned to {target_type} {target_id}")
        return True, f"Asignado a {target_type} existente", target_object
        
    except model.DoesNotExist:
        return False, f"{target_type} con ID {target_id} no encontrado", None


def _create_from_inbox(item, target_type, user):
    """
    Crea un nuevo objeto a partir de un item de inbox
    """
    if not user:
        return False, "Se requiere usuario para crear objetos", None
    
    managers = get_managers_for_user(user)
    
    try:
        if target_type == 'task':
            task = managers['task_manager'].create_task(
                title=item.title,
                description=item.description or item.content,
                important=False
            )
            item.processed_to = task
            result = task
            
        elif target_type == 'project':
            project = managers['project_manager'].create_project(
                title=item.title,
                description=item.description or item.content,
                event=None
            )
            item.processed_to = project
            result = project
            
        elif target_type == 'event':
            default_status = get_default_status('event')
            event = Event.objects.create(
                title=item.title,
                description=item.description or item.content,
                event_status=default_status,
                host=user,
                assigned_to=user
            )
            item.processed_to = event
            result = event
            
        else:
            return False, f"Tipo inválido para creación: {target_type}", None
        
        # Marcar como procesado
        item.is_processed = True
        item.processed_at = timezone.now()
        item.processed_by = user
        item.save()
        
        logger.info(f"Inbox item {item.id} created new {target_type} {result.id}")
        return True, f"{target_type.capitalize()} creado exitosamente", result
        
    except Exception as e:
        logger.exception(f"Error creating {target_type} from inbox item {item.id}: {e}")
        return False, f"Error al crear {target_type}: {str(e)}", None


# Alias para compatibilidad
create_from_inbox = _create_from_inbox
