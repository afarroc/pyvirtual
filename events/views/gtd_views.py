# gtd_views.py

# ============================================================================
# IMPORTACIONES ESTÁNDAR DE PYTHON
# ============================================================================
import json
import re
import logging
import datetime  # Importar datetime completo
from datetime import timedelta, time
from difflib import SequenceMatcher

# ============================================================================
# IMPORTACIONES DE DJANGO
# ============================================================================
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model

User = get_user_model()
from django.contrib.contenttypes.models import ContentType
from django.db import transaction, models
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.utils import timezone

# ============================================================================
# IMPORTACIONES DE LA APLICACIÓN
# ============================================================================
from ..models import (
    InboxItem, InboxItemClassification, InboxItemAuthorization, 
    InboxItemHistory, Task, Project, Event, Status,  # Añadir Event y Status
    GTDProcessingSettings, TaskStatus, ProjectStatus  # Añadir TaskStatus y ProjectStatus
)
from ..management.task_manager import TaskManager
from ..management.project_manager import ProjectManager
from ..management.event_manager import EventManager  # Añadir EventManager

# utils
from ..utils.project_utils import create_consistent_project


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================
def find_similar_tasks(user, title, description=None, threshold=0.6):
    """
    Busca tareas similares basadas en similitud de texto
    """
    # Obtener todas las tareas del usuario
    user_tasks = Task.objects.filter(
        Q(host=user) | Q(assigned_to=user)
    ).select_related('task_status', 'project', 'event')

    similar_tasks = []

    # Normalizar texto para comparación
    def normalize_text(text):
        if not text:
            return ""
        return re.sub(r'[^\w\s]', '', text.lower().strip())

    normalized_title = normalize_text(title)
    normalized_description = normalize_text(description) if description else ""

    for task in user_tasks:
        # Calcular similitud del título
        task_title_norm = normalize_text(task.title)
        title_similarity = SequenceMatcher(None, normalized_title, task_title_norm).ratio()

        # Calcular similitud de la descripción si existe
        desc_similarity = 0
        if normalized_description and task.description:
            task_desc_norm = normalize_text(task.description)
            desc_similarity = SequenceMatcher(None, normalized_description, task_desc_norm).ratio()
        elif not normalized_description and not task.description:
            desc_similarity = 0.5  # Considerar como parcialmente similar si ambos están vacíos

        # Calcular similitud ponderada (título tiene más peso)
        overall_similarity = (title_similarity * 0.7) + (desc_similarity * 0.3)

        if overall_similarity >= threshold:
            similar_tasks.append({
                'task': task,
                'similarity': overall_similarity,
                'title_similarity': title_similarity,
                'description_similarity': desc_similarity
            })

    # Ordenar por similitud descendente
    similar_tasks.sort(key=lambda x: x['similarity'], reverse=True)
    return similar_tasks

def find_similar_projects(user, title, description=None, threshold=0.6):
    """
    Busca proyectos similares basados en similitud de texto
    """
    # Obtener todos los proyectos del usuario
    user_projects = Project.objects.filter(
        Q(host=user) | Q(assigned_to=user) | Q(attendees=user)
    ).distinct().select_related('project_status', 'event')

    similar_projects = []

    # Normalizar texto para comparación
    def normalize_text(text):
        if not text:
            return ""
        return re.sub(r'[^\w\s]', '', text.lower().strip())

    normalized_title = normalize_text(title)
    normalized_description = normalize_text(description) if description else ""

    for project in user_projects:
        # Calcular similitud del título
        project_title_norm = normalize_text(project.title)
        title_similarity = SequenceMatcher(None, normalized_title, project_title_norm).ratio()

        # Calcular similitud de la descripción si existe
        desc_similarity = 0
        if normalized_description and project.description:
            project_desc_norm = normalize_text(project.description)
            desc_similarity = SequenceMatcher(None, normalized_description, project_desc_norm).ratio()
        elif not normalized_description and not project.description:
            desc_similarity = 0.5  # Considerar como parcialmente similar si ambos están vacíos

        # Calcular similitud ponderada (título tiene más peso)
        overall_similarity = (title_similarity * 0.7) + (desc_similarity * 0.3)

        if overall_similarity >= threshold:
            similar_projects.append({
                'project': project,
                'similarity': overall_similarity,
                'title_similarity': title_similarity,
                'description_similarity': desc_similarity
            })

    # Ordenar por similitud descendente
    similar_projects.sort(key=lambda x: x['similarity'], reverse=True)
    return similar_projects

# ============================================================================
# NUEVAS FUNCIONES AUXILIARES DE CREACIÓN (AGREGAR DESPUÉS DE LAS EXISTENTES)
# ============================================================================

def _create_event_for_inbox_item(inbox_item, user, context_type="inbox"):
    """
    Crea un evento asociado a un item del inbox solo cuando el flujo
    GTD decide explícitamente generar un evento de calendario.
    Ahora retorna None por defecto; el llamador debe decidir si create.
    """
    return None

# gtd_views.py - en la función _create_project_with_event

# En gtd_views.py - reemplazar llamadas a _create_project_with_event


def _create_project_with_event(inbox_item, user, event=None):
    """
    Crea un proyecto asociado a un evento (nuevo o existente)
    Usando la función helper consistente
    """
    try:
        project, created_event = create_consistent_project(
            user=user,
            title=inbox_item.title,
            description=inbox_item.description,
            assigned_to=user,
            event=event,
            ticket_price=0.07
        )
        return project, created_event
    except Exception as e:
        raise Exception(f"Error creando proyecto: {e}")

def _create_task_with_context(inbox_item, user, project=None, event=None, assigned_to=None):
    """
    Crea una tarea con contexto completo (evento, proyecto)
    """
    try:
        task_manager = TaskManager(user)
        
        # Determinar asignación
        task_assigned_to = assigned_to or user
        
        # No crear eventos automáticamente. El evento debe ser provisto
        # explícitamente por el flujo o por el usuario.
        
        # Si hay proyecto pero no evento, usar evento del proyecto si existe
        if project and not event and hasattr(project, 'event'):
            event = project.event
        
        # Crear tarea usando el TaskManager
        task = task_manager.create_task(
            title=inbox_item.title,
            description=inbox_item.description,
            important=False,
            project=project,  # Puede ser None, proyecto nuevo o existente
            event=event,      # Evento nuevo, del proyecto o None
            task_status=None,  # Usará 'To Do' por defecto
            assigned_to=task_assigned_to,
            ticket_price=0.07
        )
        
        return task, event
    except Exception as e:
        raise Exception(f"Error creando tarea: {e}")

# En gtd_views.py, actualizar la función _link_inbox_to_object:

def _link_inbox_to_object(inbox_item, user, content_object, content_type):
    """
    Vincula un item del inbox a un objeto existente usando GenericForeignKey
    Con validación mejorada
    """
    try:
        with transaction.atomic():
            # Obtener ContentType del objeto
            object_content_type = ContentType.objects.get_for_model(content_object.__class__)
            
            # Verificar que el objeto exista
            if not content_object.id:
                raise ValueError("El objeto destino no tiene ID válido")
            
            # Log de depuración
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"DEBUG LINK: Vincular inbox {inbox_item.id} a objeto tipo {content_object.__class__.__name__} ID {content_object.id}")
            logger.info(f"DEBUG LINK: ContentType: {object_content_type.app_label}.{object_content_type.model}")
            
            # Marcar como procesado y vincular
            inbox_item.is_processed = True
            inbox_item.processed_to_content_type = object_content_type
            inbox_item.processed_to_object_id = content_object.id
            inbox_item.processed_at = timezone.now()
            inbox_item.save()
            
            # Forzar la recarga de relaciones
            inbox_item.refresh_from_db()
            
            # Registrar en historial
            InboxItemHistory.objects.create(
                inbox_item=inbox_item,
                user=user,
                action=f'linked_to_{content_type}',
                new_values={
                    f'linked_{content_type}_id': content_object.id,
                    f'linked_{content_type}_title': getattr(content_object, 'title', 'Sin título'),
                    'link_method': 'manual_selection',
                    'linked_object_type': content_object.__class__.__name__,
                    'content_type_id': object_content_type.id,
                    'object_id': content_object.id
                }
            )
            
            # Verificar que el enlace se creó correctamente
            try:
                linked_object = inbox_item.processed_to
                logger.info(f"DEBUG LINK: Verificación - linked_object: {linked_object}")
                logger.info(f"DEBUG LINK: Verificación - tipo: {type(linked_object).__name__ if linked_object else 'None'}")
                logger.info(f"DEBUG LINK: Verificación - id: {getattr(linked_object, 'id', 'N/A') if linked_object else 'N/A'}")
                logger.info(f"DEBUG LINK: Verificación - title: {getattr(linked_object, 'title', 'N/A') if linked_object else 'N/A'}")
                
                if not linked_object:
                    raise ValueError(f"Error: processed_to es None")
                
                # Verificación adicional - obtener directamente de la base de datos
                try:
                    ModelClass = object_content_type.model_class()
                    db_object = ModelClass.objects.get(id=content_object.id)
                    logger.info(f"DEBUG LINK: Verificación DB - objeto existe: {db_object.title if hasattr(db_object, 'title') else 'Sin título'}")
                except Exception as db_error:
                    logger.error(f"DEBUG LINK: Error verificando en base de datos: {db_error}")
                
                return True
            except Exception as link_error:
                logger.error(f"DEBUG LINK: Error verificando enlace: {link_error}")
                raise
            
    except Exception as e:
        logger.error(f"Error vinculando inbox: {e}", exc_info=True)
        return False

# ============================================================================
# VISTAS GTD
# ============================================================================

@login_required
def inbox_view(request):
    """
    Vista de la bandeja de entrada GTD para capturar tareas rápidamente
    """
    if request.method == 'POST':
        # Crear nuevo item en el inbox
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()

        if title:
            # Crear item con categorización inicial
            inbox_item = InboxItem.objects.create(
                title=title,
                description=description,
                created_by=request.user,
                gtd_category='pendiente',
                priority='media'
            )

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Item agregado al inbox correctamente',
                    'item_id': inbox_item.id
                })
            else:
                messages.success(request, 'Item agregado al inbox correctamente')
                return redirect('events:inbox')
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': 'El título es obligatorio'
                })
            else:
                messages.error(request, 'El título es obligatorio')
                return redirect('events:inbox')

    # Obtener items del inbox del usuario (creados por él o asignados a él)
    inbox_items = InboxItem.objects.filter(
        models.Q(created_by=request.user) | models.Q(assigned_to=request.user)
    ).distinct()

    # Categorización GTD
    unprocessed_items = inbox_items.filter(is_processed=False)
    processed_items = inbox_items.filter(is_processed=True)

    # Items por categoría GTD
    accionables = unprocessed_items.filter(gtd_category='accionable')
    no_accionables = unprocessed_items.filter(gtd_category='no_accionable')
    pendientes = unprocessed_items.filter(gtd_category='pendiente')

    # Items por tipo de acción
    hacer_items = unprocessed_items.filter(action_type='hacer')
    delegar_items = unprocessed_items.filter(action_type='delegar')
    posponer_items = unprocessed_items.filter(action_type='posponer')
    proyecto_items = unprocessed_items.filter(action_type='proyecto')
    eliminar_items = unprocessed_items.filter(action_type='eliminar')
    archivar_items = unprocessed_items.filter(action_type='archivar')
    incubar_items = unprocessed_items.filter(action_type='incubar')

    # Estadísticas GTD
    gtd_stats = {
        'total': unprocessed_items.count(),
        'accionables': accionables.count(),
        'no_accionables': no_accionables.count(),
        'pendientes': pendientes.count(),
        'hacer': hacer_items.count(),
        'delegar': delegar_items.count(),
        'posponer': posponer_items.count(),
        'proyectos': proyecto_items.count(),
        'eliminar': eliminar_items.count(),
        'archivar': archivar_items.count(),
        'incubar': incubar_items.count(),
    }

    context = {
        'title': 'Bandeja de Entrada GTD',
        'unprocessed_items': unprocessed_items,
        'processed_items': processed_items,
        'total_unprocessed': unprocessed_items.count(),
        'total_processed': processed_items.count(),

        # Categorización GTD
        'accionables': accionables,
        'no_accionables': no_accionables,
        'pendientes': pendientes,

        # Tipos de acción
        'hacer_items': hacer_items,
        'delegar_items': delegar_items,
        'posponer_items': posponer_items,
        'proyecto_items': proyecto_items,
        'eliminar_items': eliminar_items,
        'archivar_items': archivar_items,
        'incubar_items': incubar_items,

        # Estadísticas
        'gtd_stats': gtd_stats,
    }

    return render(request, 'events/inbox.html', context)

@login_required
def event_inbox_panel(request):
    """
    Vista para mostrar items del inbox filtrados por usuario actual en formato tabla simple
    Sección event/inbox/* y /panel/
    """
    # Obtener items del inbox del usuario (creados por él o asignados a él)
    inbox_items = InboxItem.objects.filter(
        models.Q(created_by=request.user) | models.Q(assigned_to=request.user)
    ).distinct().select_related('created_by', 'assigned_to').order_by('-created_at')

    # Estadísticas básicas
    total_items = inbox_items.count()
    unprocessed_items = inbox_items.filter(is_processed=False).count()
    processed_items = inbox_items.filter(is_processed=True).count()

    # Items recientes (últimos 7 días)
    recent_items = inbox_items.filter(created_at__gte=timezone.now() - timedelta(days=7))

    # Datos para la tabla
    table_data = []
    for item in inbox_items[:50]:  # Limitar a 50 items para mejor rendimiento
        table_data.append({
            'id': item.id,
            'title': item.title,
            'description': item.description[:100] + '...' if item.description and len(item.description) > 100 else item.description,
            'created_by': item.created_by.username if item.created_by else 'Sistema',
            'assigned_to': item.assigned_to.username if item.assigned_to else 'Sin asignar',
            'created_at': item.created_at.strftime('%d/%m/%Y %H:%M'),
            'is_processed': item.is_processed,
            'gtd_category': item.gtd_category,
            'priority': item.priority,
            'action_type': item.action_type,
        })

    context = {
        'title': 'Panel de Inbox - Items Filtrados',
        'inbox_items': inbox_items,
        'table_data': table_data,
        'total_items': total_items,
        'unprocessed_items': unprocessed_items,
        'processed_items': processed_items,
        'recent_items': recent_items.count(),
    }

    return render(request, 'events/inbox_panel.html', context)

@login_required
def inbox_stats_api(request):
    """
    API endpoint para obtener estadísticas del inbox GTD en tiempo real
    """
    if request.method != 'GET':
        return JsonResponse({'success': False, 'error': 'Método no permitido'})

    try:
        # Obtener items del inbox del usuario
        # SU users can see all items, others see only their own or assigned items
        if hasattr(request.user, 'cv') and hasattr(request.user.cv, 'role') and request.user.cv.role == 'SU':
            # SU users see all inbox items
            inbox_items = InboxItem.objects.all()
        else:
            # Regular users see items they created or are assigned to
            inbox_items = InboxItem.objects.filter(
                models.Q(created_by=request.user) | models.Q(assigned_to=request.user)
            ).distinct()

        # Estadísticas básicas
        total_items = inbox_items.count()
        unprocessed_items = inbox_items.filter(is_processed=False)
        processed_items = inbox_items.filter(is_processed=True)

        # Items por categoría GTD
        accionables = unprocessed_items.filter(gtd_category='accionable')
        no_accionables = unprocessed_items.filter(gtd_category='no_accionable')
        pendientes = unprocessed_items.filter(gtd_category='pendiente')

        # Items por tipo de acción
        hacer_items = unprocessed_items.filter(action_type='hacer')
        delegar_items = unprocessed_items.filter(action_type='delegar')
        posponer_items = unprocessed_items.filter(action_type='posponer')
        proyecto_items = unprocessed_items.filter(action_type='proyecto')
        eliminar_items = unprocessed_items.filter(action_type='eliminar')
        archivar_items = unprocessed_items.filter(action_type='archivar')
        incubar_items = unprocessed_items.filter(action_type='incubar')

        # Items de hoy
        today = timezone.now().date()
        today_start = timezone.make_aware(datetime.combine(today, time.min))
        today_end = timezone.make_aware(datetime.combine(today, time.max))
        today_items = inbox_items.filter(created_at__range=(today_start, today_end))

        # Items recientes (últimas 24 horas)
        last_24h = timezone.now() - timedelta(hours=24)
        recent_items = inbox_items.filter(created_at__gte=last_24h)

        # Estadísticas detalladas
        stats = {
            'total': total_items,
            'unprocessed': unprocessed_items.count(),
            'processed': processed_items.count(),
            'today': today_items.count(),
            'recent': recent_items.count(),
            'gtd_categories': {
                'accionables': accionables.count(),
                'no_accionables': no_accionables.count(),
                'pendientes': pendientes.count(),
            },
            'action_types': {
                'hacer': hacer_items.count(),
                'delegar': delegar_items.count(),
                'posponer': posponer_items.count(),
                'proyectos': proyecto_items.count(),
                'eliminar': eliminar_items.count(),
                'archivar': archivar_items.count(),
                'incubar': incubar_items.count(),
            },
            'percentages': {
                'processed_rate': round((processed_items.count() / total_items * 100), 1) if total_items > 0 else 0,
                'unprocessed_rate': round((unprocessed_items.count() / total_items * 100), 1) if total_items > 0 else 0,
                'today_rate': round((today_items.count() / total_items * 100), 1) if total_items > 0 else 0,
            },
            'trends': {
                'today_vs_yesterday': today_items.count() - inbox_items.filter(
                    created_at__range=(
                        today_start - timedelta(days=1),
                        today_end - timedelta(days=1)
                    )
                ).count(),
                'processed_today': processed_items.filter(processed_at__date=today).count(),
            }
        }

        return JsonResponse({
            'success': True,
            'stats': stats,
            'timestamp': timezone.now().isoformat()
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@login_required
def process_inbox_item(request, item_id=None):
    """
    Vista para procesar items del inbox siguiendo GTD
    Ahora integra eventos con proyectos y tareas
    """
    logger = logging.getLogger(__name__)
    
    # Si no hay item_id, mostrar bandeja general
    if item_id is None:
        return _render_inbox_list(request)
    
    # Procesar item específico
    return _process_single_inbox_item(request, item_id, logger)

def _render_inbox_list(request):
    """Renderiza la lista de items del inbox"""
    user_inbox_items = InboxItem.objects.filter(
        Q(created_by=request.user) |
        Q(assigned_to=request.user) |
        Q(authorized_users=request.user) |
        Q(is_public=True)
    ).distinct().select_related('created_by', 'assigned_to').order_by('-created_at')
    
    context = {
        'title': 'Bandeja de Entrada GTD',
        'inbox_items': user_inbox_items,
        'total_items': user_inbox_items.count(),
        'unprocessed_count': user_inbox_items.filter(is_processed=False).count(),
        'processed_count': user_inbox_items.filter(is_processed=True).count(),
    }
    return render(request, 'events/inbox_mailbox.html', context)

def _process_single_inbox_item(request, item_id, logger):
    """Procesa un item específico del inbox"""
    try:
        inbox_item = InboxItem.objects.filter(
            Q(created_by=request.user) |
            Q(assigned_to=request.user) |
            Q(authorized_users=request.user) |
            Q(is_public=True)
        ).distinct().get(id=item_id)
        
        # Log de acceso
        logger.info(f"User {request.user.username} processing inbox item {item_id}")
        
    except InboxItem.DoesNotExist:
        logger.warning(f"User {request.user.username} denied access to inbox item {item_id}")
        messages.error(request, 'Item no encontrado o no tienes permisos')
        return redirect('events:process_inbox_item_mailbox')
    
    # Manejar POST request
    if request.method == 'POST':
        return _handle_post_action(request, inbox_item, item_id, logger)
    
    # GET request - mostrar formulario
    return _render_processing_form(request, inbox_item)

def _handle_post_action(request, inbox_item, item_id, logger):
    """Maneja las acciones POST del formulario"""
    action = request.POST.get('action')
    gtd_category = request.POST.get('gtd_category')
    action_type = request.POST.get('action_type')
    
    # Actualizar categorización GTD
    if gtd_category:
        inbox_item.gtd_category = gtd_category
    if action_type:
        inbox_item.action_type = action_type
    inbox_item.save()
    
    # Mapeo de acciones a handlers
    action_handlers = {
        'convert_to_task': _handle_convert_to_task,
        'convert_to_project': _handle_convert_to_project,
        'convert_to_event': _handle_convert_to_event,
        'convert_to_task_project': _handle_convert_to_task_project,
        'link_to_task': _handle_link_to_task,
        'link_to_project': _handle_link_to_project,
        'link_to_event': _handle_link_to_event,
        'delete': _handle_delete,
        'postpone': _handle_postpone,
        'categorize': _handle_categorize,
        'reference': _handle_reference,
        'someday': _handle_someday,
    }
    
    handler = action_handlers.get(action)
    if handler:
        return handler(request, inbox_item, item_id, logger)
    
    # Acciones de modal (no procesan)
    if action in ['choose_existing_task', 'choose_existing_project', 'choose_existing_event']:
        return redirect('events:process_inbox_item', item_id=item_id)
    
    messages.error(request, 'Acción no reconocida')
    return redirect('events:process_inbox_item', item_id=item_id)

# ============================================================================
# HANDLERS DE ACCIONES ESPECÍFICAS
# ============================================================================
def _handle_convert_to_task(request, inbox_item, item_id, logger):
    """Convierte inbox item a tarea con opciones de contexto"""
    try:
        # Obtener opciones del formulario - VERIFICAR QUE ESTOS CAMPOS EXISTEN
        project_option = request.POST.get('project_option', 'none')
        event_option = request.POST.get('event_option', 'new')
        existing_project_id = request.POST.get('existing_project_id')
        existing_event_id = request.POST.get('existing_event_id')
        assigned_to_id = request.POST.get('assigned_to')
        
        # Log para depuración
        logger.info(f"DEBUG - project_option: {project_option}")
        logger.info(f"DEBUG - event_option: {event_option}")
        logger.info(f"DEBUG - existing_project_id: {existing_project_id}")
        logger.info(f"DEBUG - existing_event_id: {existing_event_id}")
        logger.info(f"DEBUG - assigned_to_id: {assigned_to_id}")
        
        # Resto del código...

        assigned_user = request.user
        if assigned_to_id:
            try:
                assigned_user = User.objects.get(id=assigned_to_id)
            except User.DoesNotExist:
                pass
        
        project = None
        event = None
        
        # Manejar opciones de proyecto
        if project_option == 'new':
            # Crear nuevo proyecto con evento
            project, event = _create_project_with_event(inbox_item, request.user, event=None)
            messages.info(request, f'Proyecto "{project.title}" creado automáticamente')
        elif project_option == 'existing' and existing_project_id:
            try:
                project = Project.objects.get(id=existing_project_id)
                # Verificar permisos
                if not _has_project_permission(project, request.user):
                    messages.error(request, 'No tienes permisos para usar este proyecto')
                    return redirect('events:process_inbox_item', item_id=item_id)
            except Project.DoesNotExist:
                messages.error(request, 'Proyecto no encontrado')
                return redirect('events:process_inbox_item', item_id=item_id)
        
        # Manejar opciones de evento
        if event_option == 'existing' and existing_event_id:
            try:
                event = Event.objects.get(id=existing_event_id)
                if not _has_event_permission(event, request.user):
                    messages.error(request, 'No tienes permisos para usar este evento')
                    return redirect('events:process_inbox_item', item_id=item_id)
            except Event.DoesNotExist:
                messages.error(request, 'Evento no encontrado')
                return redirect('events:process_inbox_item', item_id=item_id)
        elif event_option == 'new' and not event:
            # Solo crear evento si no se creó con proyecto
            event = _create_event_for_inbox_item(inbox_item, request.user, "task")
        
        # Crear tarea con contexto
        task, created_event = _create_task_with_context(
            inbox_item, request.user, 
            project=project, 
            event=event,
            assigned_to=assigned_user
        )
        
        # Vincular inbox a la tarea
        if _link_inbox_to_object(inbox_item, request.user, task, 'task'):
            success_message = f'Tarea "{task.title}" creada exitosamente.'
            if project:
                success_message += f' Proyecto: {project.title}'
            else:
                success_message += ' Sin proyecto'
            
            if created_event:
                success_message += f', Evento: {created_event.title}'
            else:
                success_message += ', Sin evento'
            
            messages.success(request, success_message)
            
            # Redirigir al inbox general
            return redirect('events:process_inbox_item_mailbox')
        else:
            messages.error(request, 'Error al vincular el item del inbox')
            return redirect('events:process_inbox_item', item_id=item_id)
            
    except Exception as e:
        logger.error(f"Error creating task from inbox: {str(e)}", exc_info=True)
        messages.error(request, f'Error al crear la tarea: {e}')
        return redirect('events:process_inbox_item', item_id=item_id)

def _handle_convert_to_project(request, inbox_item, item_id, logger):
    """Convierte inbox item a proyecto con evento"""
    try:
        event_option = request.POST.get('event_option', 'new')
        existing_event_id = request.POST.get('existing_event_id')
        
        event = None
        
        # Manejar opciones de evento
        if event_option == 'existing' and existing_event_id:
            try:
                event = Event.objects.get(id=existing_event_id)
                if not _has_event_permission(event, request.user):
                    messages.error(request, 'No tienes permisos para usar este evento')
                    return redirect('events:process_inbox_item', item_id=item_id)
            except Event.DoesNotExist:
                messages.error(request, 'Evento no encontrado')
                return redirect('events:process_inbox_item', item_id=item_id)
        
        # Crear proyecto con evento
        project, created_event = _create_project_with_event(inbox_item, request.user, event)
        
        # Vincular inbox al proyecto
        if project and _link_inbox_to_object(inbox_item, request.user, project, 'project'):
            success_message = f'Proyecto "{project.title}" creado exitosamente.'
            if created_event:
                success_message += f' Evento: {created_event.title}'
            else:
                success_message += ' Vinculado a evento existente'
            
            messages.success(request, success_message)
            
            # DEBUG: Registrar en logs
            logger.info(f"DEBUG: Inbox item {item_id} vinculado a proyecto {project.id} - {project.title}")
            logger.info(f"DEBUG: Inbox item procesado a: {inbox_item.processed_to}")
            
            # Redirigir al inbox general
            return redirect('events:process_inbox_item_mailbox')
        else:
            messages.error(request, 'Error al crear o vincular el proyecto')
            return redirect('events:process_inbox_item', item_id=item_id)
            
    except Exception as e:
        logger.error(f"Error creating project from inbox: {str(e)}", exc_info=True)
        messages.error(request, f'Error al crear el proyecto: {e}')
        return redirect('events:process_inbox_item', item_id=item_id)

def _handle_convert_to_event(request, inbox_item, item_id, logger):
    """Convierte inbox item a evento"""
    try:
        event = _create_event_for_inbox_item(inbox_item, request.user, "direct")
        
        if event and _link_inbox_to_object(inbox_item, request.user, event, 'event'):
            messages.success(request, f'Evento "{event.title}" creado exitosamente')
            # Redirigir al inbox general
            return redirect('events:process_inbox_item_mailbox')
        else:
            messages.error(request, 'Error al crear el evento')
            return redirect('events:process_inbox_item', item_id=item_id)
            
    except Exception as e:
        logger.error(f"Error creating event from inbox: {str(e)}", exc_info=True)
        messages.error(request, f'Error al crear el evento: {e}')
        return redirect('events:process_inbox_item', item_id=item_id)

def _handle_convert_to_task_project(request, inbox_item, item_id, logger):
    """Convierte inbox item a proyecto con tarea inicial"""
    try:
        # Crear proyecto con evento
        project, event = _create_project_with_event(inbox_item, request.user, None)
        
        # Crear tarea inicial en el proyecto
        task, _ = _create_task_with_context(
            inbox_item, request.user,
            project=project,
            event=event,
            assigned_to=request.user
        )
        
        # Vincular inbox al proyecto (la tarea queda vinculada a través del proyecto)
        if _link_inbox_to_object(inbox_item, request.user, project, 'project'):
            messages.success(request, 
                f'Proyecto "{project.title}" creado con tarea inicial "{task.title}". '
                f'Evento asociado: {event.title}'
            )
            # Redirigir al inbox general
            return redirect('events:process_inbox_item_mailbox')
        else:
            messages.error(request, 'Error al vincular el item del inbox')
            return redirect('events:process_inbox_item', item_id=item_id)
            
    except Exception as e:
        logger.error(f"Error creating project+task from inbox: {str(e)}", exc_info=True)
        messages.error(request, f'Error al crear proyecto con tarea: {e}')
        return redirect('events:process_inbox_item', item_id=item_id)

def _handle_link_to_task(request, inbox_item, item_id, logger):
    """Vincula inbox item a tarea existente"""
    task_id = request.POST.get('task_id')
    if not task_id:
        messages.error(request, 'Debe seleccionar una tarea para vincular.')
        return redirect('events:process_inbox_item', item_id=item_id)
    
    try:
        task_id = int(task_id)
        task = Task.objects.get(id=task_id)
        
        # Verificar permisos
        if not _has_task_permission(task, request.user):
            messages.error(request, 'No tienes permisos para vincular a esta tarea.')
            return redirect('events:process_inbox_item', item_id=item_id)
        
        # Verificar estado válido
        if task.task_status.status_name in ['Deleted', 'Archived']:
            messages.error(request, 'No se puede vincular a una tarea eliminada o archivada.')
            return redirect('events:process_inbox_item', item_id=item_id)
        
        # Vincular
        if _link_inbox_to_object(inbox_item, request.user, task, 'task'):
            messages.success(request,
                f'Item del inbox vinculado exitosamente a la tarea: "{task.title}"')
            # Redirigir al inbox general
            return redirect('events:process_inbox_item_mailbox')
        else:
            messages.error(request, 'Error al vincular el item del inbox')
            return redirect('events:process_inbox_item', item_id=item_id)
            
    except (ValueError, TypeError):
        messages.error(request, 'ID de tarea inválido.')
        return redirect('events:process_inbox_item', item_id=item_id)
    except Task.DoesNotExist:
        messages.error(request, 'La tarea objetivo no existe o no tienes permisos para accederla.')
        return redirect('events:process_inbox_item', item_id=item_id)
    except Exception as e:
        logger.error(f"Error linking to task {task_id}: {str(e)}", exc_info=True)
        messages.error(request, f'Error al vincular: {str(e)}')
        return redirect('events:process_inbox_item', item_id=item_id)

def _handle_link_to_project(request, inbox_item, item_id, logger):
    """Vincula inbox item a proyecto existente"""
    project_id = request.POST.get('project_id')
    if not project_id:
        messages.error(request, 'Debe seleccionar un proyecto para vincular.')
        return redirect('events:process_inbox_item', item_id=item_id)
    
    try:
        project = Project.objects.get(id=project_id)
        
        # Verificar permisos
        if not _has_project_permission(project, request.user):
            messages.error(request, 'No tienes permisos para vincular a este proyecto.')
            return redirect('events:process_inbox_item', item_id=item_id)
        
        # Vincular
        if _link_inbox_to_object(inbox_item, request.user, project, 'project'):
            messages.success(request,
                f'Item del inbox vinculado exitosamente al proyecto: "{project.title}"')
            # Redirigir al inbox general
            return redirect('events:process_inbox_item_mailbox')
        else:
            messages.error(request, 'Error al vincular el item del inbox')
            return redirect('events:process_inbox_item', item_id=item_id)
            
    except Project.DoesNotExist:
        messages.error(request, 'El proyecto objetivo no existe.')
        return redirect('events:process_inbox_item', item_id=item_id)
    except Exception as e:
        logger.error(f"Error linking to project {project_id}: {str(e)}", exc_info=True)
        messages.error(request, f'Error al vincular: {e}')
        return redirect('events:process_inbox_item', item_id=item_id)

def _handle_link_to_event(request, inbox_item, item_id, logger):
    """Vincula inbox item a evento existente"""
    event_id = request.POST.get('event_id')
    if not event_id:
        messages.error(request, 'Debe seleccionar un evento para vincular.')
        return redirect('events:process_inbox_item', item_id=item_id)
    
    try:
        event = Event.objects.get(id=event_id)
        
        # Verificar permisos
        if not _has_event_permission(event, request.user):
            messages.error(request, 'No tienes permisos para vincular a este evento.')
            return redirect('events:process_inbox_item', item_id=item_id)
        
        # Vincular
        if _link_inbox_to_object(inbox_item, request.user, event, 'event'):
            messages.success(request,
                f'Item del inbox vinculado exitosamente al evento: "{event.title}"')
            # Redirigir al inbox general
            return redirect('events:process_inbox_item_mailbox')
        else:
            messages.error(request, 'Error al vincular el item del inbox')
            return redirect('events:process_inbox_item', item_id=item_id)
            
    except Event.DoesNotExist:
        messages.error(request, 'El evento objetivo no existe.')
        return redirect('events:process_inbox_item', item_id=item_id)
    except Exception as e:
        logger.error(f"Error linking to event {event_id}: {str(e)}", exc_info=True)
        messages.error(request, f'Error al vincular: {e}')
        return redirect('events:process_inbox_item', item_id=item_id)

def _handle_delete(request, inbox_item, item_id, logger):
    """Elimina item del inbox"""
    inbox_item.delete()
    messages.success(request, 'Item eliminado del inbox')
    return redirect('events:process_inbox_item_mailbox')

def _handle_postpone(request, inbox_item, item_id, logger):
    """Posponer item"""
    messages.info(request, 'Item pospuesto para procesar después')
    return redirect('events:process_inbox_item_mailbox')

def _handle_categorize(request, inbox_item, item_id, logger):
    """Solo categorizar"""
    messages.success(request, f'Item categorizado como {inbox_item.gtd_category}')
    return redirect('events:process_inbox_item_mailbox')

def _handle_reference(request, inbox_item, item_id, logger):
    """Guardar como referencia"""
    inbox_item.gtd_category = 'no_accionable'
    inbox_item.action_type = 'archivar'
    inbox_item.is_processed = True
    inbox_item.processed_at = timezone.now()
    inbox_item.save()
    
    messages.success(request, f'Item "{inbox_item.title}" guardado como referencia')
    return redirect('events:process_inbox_item_mailbox')

def _handle_someday(request, inbox_item, item_id, logger):
    """Guardar para 'algún día'"""
    inbox_item.gtd_category = 'no_accionable'
    inbox_item.action_type = 'incubar'
    inbox_item.is_processed = True
    inbox_item.processed_at = timezone.now()
    inbox_item.save()
    
    messages.success(request, f'Item "{inbox_item.title}" guardado para "Algún día/Quizás"')
    return redirect('events:process_inbox_item_mailbox')
  
# ============================================================================
# FUNCIONES AUXILIARES DE PERMISOS
# ============================================================================

def _has_task_permission(task, user):
    """Verifica permisos para tarea"""
    return (
        task.host == user or
        user in task.attendees.all() or
        task.assigned_to == user or
        (hasattr(user, 'cv') and hasattr(user.cv, 'role') and
         user.cv.role in ['SU', 'ADMIN', 'GTD_ANALYST'])
    )

def _has_project_permission(project, user):
    """Verifica permisos para proyecto"""
    return (
        project.host == user or
        user in project.attendees.all() or
        project.assigned_to == user
    )

def _has_event_permission(event, user):
    """Verifica permisos para evento"""
    return (
        event.host == user or
        user in event.attendees.all() or
        event.assigned_to == user
    )

# ============================================================================
# RENDERIZADO DEL FORMULARIO
# ============================================================================

def _render_processing_form(request, inbox_item):
    """Renderiza el formulario de procesamiento"""
    # Estadísticas
    processed_count = InboxItem.objects.filter(created_by=request.user, is_processed=True).count()
    unprocessed_count = InboxItem.objects.filter(created_by=request.user, is_processed=False).count()
    
    # Búsqueda de duplicados (usa funciones existentes)
    similar_tasks = find_similar_tasks(
        user=request.user,
        title=inbox_item.title,
        description=inbox_item.description,
        threshold=0.5
    )
    
    similar_projects = find_similar_projects(
        user=request.user,
        title=inbox_item.title,
        description=inbox_item.description,
        threshold=0.5
    )
    
    # Obtener eventos, proyectos y tareas existentes del usuario
    user_events = Event.objects.filter(
        Q(host=request.user) | Q(assigned_to=request.user) | Q(attendees=request.user)
    ).distinct().order_by('-updated_at')[:20]
    
    user_projects = Project.objects.filter(
        Q(host=request.user) | Q(assigned_to=request.user) | Q(attendees=request.user)
    ).distinct().order_by('-updated_at')[:20]
    
    user_tasks = Task.objects.filter(
        Q(host=request.user) | Q(assigned_to=request.user)
    ).order_by('-updated_at')[:20]
    
    # ===== NUEVO: Obtener clasificaciones y consenso =====
    # Obtener clasificaciones existentes
    classifications = InboxItemClassification.objects.filter(
        inbox_item=inbox_item
    ).select_related('user').order_by('-created_at')
    
    # Calcular consenso
    consensus_category = inbox_item.get_classification_consensus()
    consensus_action = inbox_item.get_action_type_consensus()
    
    # Si no hay consenso, intentar calcularlo manualmente
    if not consensus_category and classifications.exists():
        # Contar votos por categoría
        category_votes = {}
        for c in classifications:
            if c.gtd_category:
                category_votes[c.gtd_category] = category_votes.get(c.gtd_category, 0) + 1
        
        if category_votes:
            consensus_category = max(category_votes, key=category_votes.get)
    
    if not consensus_action and classifications.exists():
        # Contar votos por tipo de acción
        action_votes = {}
        for c in classifications:
            if c.action_type:
                action_votes[c.action_type] = action_votes.get(c.action_type, 0) + 1
        
        if action_votes:
            consensus_action = max(action_votes, key=action_votes.get)
    # ====================================================
    
    # Categorías y opciones GTD (usa las existentes del contexto anterior)
    gtd_categories = [
        {'value': 'accionable', 'label': 'Accionable', 'icon': 'bi-check-circle', 'color': 'success'},
        {'value': 'no_accionable', 'label': 'No Accionable', 'icon': 'bi-x-circle', 'color': 'info'},
    ]
    
    action_types = [
        {'value': 'hacer', 'label': 'Hacer', 'icon': 'bi-check2', 'color': 'success', 'category': 'accionable'},
        {'value': 'delegar', 'label': 'Delegar', 'icon': 'bi-people', 'color': 'warning', 'category': 'accionable'},
        {'value': 'posponer', 'label': 'Posponer', 'icon': 'bi-clock', 'color': 'info', 'category': 'accionable'},
        {'value': 'proyecto', 'label': 'Convertir en Proyecto', 'icon': 'bi-folder-plus', 'color': 'primary', 'category': 'accionable'},
        {'value': 'eliminar', 'label': 'Eliminar', 'icon': 'bi-trash', 'color': 'danger', 'category': 'no_accionable'},
        {'value': 'archivar', 'label': 'Archivar para Referencia', 'icon': 'bi-archive', 'color': 'secondary', 'category': 'no_accionable'},
        {'value': 'incubar', 'label': 'Incubar (Algún Día)', 'icon': 'bi-lightbulb', 'color': 'light', 'category': 'no_accionable'},
        {'value': 'esperar', 'label': 'Esperar Más Información', 'icon': 'bi-hourglass', 'color': 'warning', 'category': 'no_accionable'},
    ]
    
    # Opciones de contexto para creación
    project_options = [
        {'value': 'none', 'label': 'Sin proyecto', 'description': 'Crear tarea sin proyecto'},
        {'value': 'new', 'label': 'Nuevo proyecto', 'description': 'Crear nuevo proyecto con esta tarea'},
        {'value': 'existing', 'label': 'Proyecto existente', 'description': 'Vincular a proyecto existente'},
    ]
    
    event_options = [
        {'value': 'new', 'label': 'Nuevo evento', 'description': 'Crear nuevo evento'},
        {'value': 'existing', 'label': 'Evento existente', 'description': 'Vincular a evento existente'},
        {'value': 'none', 'label': 'Sin evento', 'description': 'No asociar evento (solo para tareas sin proyecto)'},
    ]
    
    context = {
        'title': 'Procesar Item del Inbox GTD',
        'inbox_item': inbox_item,
        'processed_count': processed_count,
        'unprocessed_count': unprocessed_count,
        
        # Resultados de búsqueda
        'similar_tasks': similar_tasks,
        'similar_projects': similar_projects,
        'has_similar_items': len(similar_tasks) + len(similar_projects) > 0,
        
        # Objetos existentes para vincular
        'user_events': user_events,
        'user_projects': user_projects,
        'user_tasks': user_tasks,
        
        # ===== NUEVO: Datos de clasificación y consenso =====
        'classifications': classifications,
        'consensus_category': consensus_category,
        'consensus_action': consensus_action,
        # ====================================================
        
        # Opciones GTD
        'gtd_categories': gtd_categories,
        'action_types': action_types,
        
        # Opciones de creación
        'project_options': project_options,
        'event_options': event_options,
        
        # Usuarios para delegación
        'available_users': User.objects.filter(is_active=True).exclude(id=request.user.id)[:10],
    }
    
    # Log para depuración
    logger = logging.getLogger(__name__)
    logger.info(f"DEBUG - Consensus category: {consensus_category}")
    logger.info(f"DEBUG - Consensus action: {consensus_action}")
    logger.info(f"DEBUG - Classifications count: {classifications.count()}")
    
    return render(request, 'events/process_inbox_item.html', context)

# ============================================================================
# NUEVOS ENDPOINTS API PARA OBTENER DATOS
# ============================================================================

@login_required
def get_inbox_creation_options(request):
    """
    API endpoint para obtener opciones de creación desde el inbox
    """
    if request.method != 'GET':
        return JsonResponse({'success': False, 'error': 'Método no permitido'})
    
    try:
        # Obtener eventos recientes
        recent_events = Event.objects.filter(
            Q(host=request.user) | Q(assigned_to=request.user)
        ).order_by('-updated_at')[:10]
        
        # Obtener proyectos recientes
        recent_projects = Project.objects.filter(
            Q(host=request.user) | Q(assigned_to=request.user)
        ).order_by('-updated_at')[:10]
        
        # Obtener estados disponibles
        statuses = {
            'event': list(Status.objects.values('id', 'status_name')),
            'project': list(ProjectStatus.objects.values('id', 'status_name')),
            'task': list(TaskStatus.objects.values('id', 'status_name')),
        }
        
        return JsonResponse({
            'success': True,
            'events': [
                {'id': e.id, 'title': e.title, 'status': e.event_status.status_name}
                for e in recent_events
            ],
            'projects': [
                {'id': p.id, 'title': p.title, 'status': p.project_status.status_name}
                for p in recent_projects
            ],
            'statuses': statuses,
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@login_required
def create_from_inbox_api(request):
    """
    API endpoint para creación rápida desde inbox
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'})
    
    try:
        action = request.POST.get('action')
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        
        if not title:
            return JsonResponse({'success': False, 'error': 'El título es requerido'})
        
        # Crear item en inbox primero
        inbox_item = InboxItem.objects.create(
            title=title,
            description=description,
            created_by=request.user,
            gtd_category='accionable',
            priority='media'
        )
        
        result = {
            'success': True,
            'inbox_item_id': inbox_item.id,
            'message': 'Item creado en inbox'
        }
        
        # Procesar inmediatamente si se especifica acción
        if action:
            # Aquí podrías llamar a los handlers directamente
            # Por ahora solo registramos
            result['action'] = action
            result['message'] = f'Item creado y listo para {action}'
        
        return JsonResponse(result)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

# ============================================================================
# SISTEMA DE ADMINISTRACIÓN DE INBOX
# ============================================================================

@login_required
def inbox_admin_dashboard(request):
    """
    Panel de administración de inboxes - Vista principal para gestionar items del inbox
    """
    # Verificar permisos de administrador
    if not (hasattr(request.user, 'cv') and hasattr(request.user.cv, 'role') and request.user.cv.role in ['SU', 'ADMIN']):
        messages.error(request, 'No tienes permisos para acceder al panel de administración de inboxes.')
        return redirect('events:inbox')

    # Filtros
    status_filter = request.GET.get('status', 'all')
    category_filter = request.GET.get('category', 'all')
    user_filter = request.GET.get('user', 'all')
    search_query = request.GET.get('search', '')

    # Base queryset
    inbox_items = InboxItem.objects.select_related(
        'created_by'
    ).prefetch_related(
        'authorized_users',
        'classification_votes',
        'inboxitemclassification_set'
    )

    # Aplicar filtros
    if status_filter == 'processed':
        inbox_items = inbox_items.filter(is_processed=True)
    elif status_filter == 'unprocessed':
        inbox_items = inbox_items.filter(is_processed=False)
    elif status_filter == 'public':
        inbox_items = inbox_items.filter(is_public=True)

    if category_filter != 'all':
        inbox_items = inbox_items.filter(gtd_category=category_filter)

    if user_filter != 'all':
        inbox_items = inbox_items.filter(created_by=user_filter)

    if search_query:
        inbox_items = inbox_items.filter(
            models.Q(title__icontains=search_query) |
            models.Q(description__icontains=search_query) |
            models.Q(created_by__username__icontains=search_query)
        )

    # Estadísticas generales
    stats = {
        'total': InboxItem.objects.count(),
        'processed': InboxItem.objects.filter(is_processed=True).count(),
        'unprocessed': InboxItem.objects.filter(is_processed=False).count(),
        'public': InboxItem.objects.filter(is_public=True).count(),
        'private': InboxItem.objects.filter(is_public=False).count(),
        'today': InboxItem.objects.filter(created_at__date=timezone.now().date()).count(),
        'this_week': InboxItem.objects.filter(created_at__gte=timezone.now() - timedelta(days=7)).count(),
    }

    # Items recientes
    recent_items = inbox_items[:10]

    # Usuarios activos
    active_users = User.objects.filter(
        models.Q(inboxitem__isnull=False) |
        models.Q(authorized_inbox_items__isnull=False) |
        models.Q(classified_inbox_items__isnull=False)
    ).distinct()[:20]

    context = {
        'title': 'Administración de Inbox GTD',
        'inbox_items': inbox_items,
        'recent_items': recent_items,
        'stats': stats,
        'active_users': active_users,
        'status_filter': status_filter,
        'category_filter': category_filter,
        'user_filter': user_filter,
        'search_query': search_query,
    }

    return render(request, 'events/inbox_admin_dashboard.html', context)

@login_required
def inbox_item_detail_admin(request, item_id):
    """
    Vista detallada de un item del inbox para administración
    """
    # Verificar permisos - permitir acceso a usuarios autenticados y activos
    if not request.user.is_authenticated:
        messages.error(request, 'Debes iniciar sesión para ver detalles de items del inbox.')
        return redirect('login')

    if not request.user.is_active:
        messages.error(request, 'Tu cuenta no está activa.')
        return redirect('login')

    try:
        inbox_item = InboxItem.objects.select_related(
            'created_by'
        ).prefetch_related(
            'authorized_users',
            'classification_votes',
            'inboxitemclassification_set__user',
            'inboxitemauthorization_set__user'
        ).get(id=item_id)

        # Incrementar contador de vistas
        inbox_item.increment_views()

        # Obtener clasificaciones existentes
        classifications = inbox_item.inboxitemclassification_set.all()

        # Calcular consenso
        consensus_category = inbox_item.get_classification_consensus()
        consensus_action = inbox_item.get_action_type_consensus()

        # Historial de actividad
        activity_history = InboxItemHistory.objects.filter(inbox_item=inbox_item)[:20]

        # Obtener usuarios disponibles para delegación
        available_users = User.objects.filter(is_active=True).order_by('username')

        context = {
            'title': f'Administrar: {inbox_item.title}',
            'item': inbox_item,
            'classifications': classifications,
            'consensus_category': consensus_category,
            'consensus_action': consensus_action,
            'history': activity_history,
            'available_users': available_users,
        }

        # Debug logs
        logger = logging.getLogger(__name__)
        logger.info(f"DEBUG: Rendering inbox_item_detail_admin for item {item_id}")
        logger.info(f"DEBUG: Item title: {inbox_item.title}")
        logger.info(f"DEBUG: Item description: {inbox_item.description}")
        logger.info(f"DEBUG: Item created_by: {inbox_item.created_by}")
        logger.info(f"DEBUG: Item created_at: {inbox_item.created_at}")
        logger.info(f"DEBUG: Context keys: {list(context.keys())}")
        logger.info(f"DEBUG: Available users count: {available_users.count()}")
        logger.info(f"DEBUG: History count: {activity_history.count()}")

        return render(request, 'events/inbox_item_detail_admin.html', context)

    except InboxItem.DoesNotExist:
        messages.error(request, 'Item del inbox no encontrado.')
        return redirect('events:inbox_admin_dashboard')

@login_required
def classify_inbox_item_admin(request, item_id):
    """
    Vista para clasificar un item del inbox desde el panel de administración
    """
    # Verificar permisos
    if not (hasattr(request.user, 'cv') and request.user.cv and request.user.cv.role in ['SU', 'ADMIN', 'GTD_ANALYST']):
        messages.error(request, 'No tienes permisos para clasificar items del inbox.')
        return redirect('events:inbox_admin_dashboard')

    try:
        inbox_item = InboxItem.objects.get(id=item_id)
    except InboxItem.DoesNotExist:
        messages.error(request, 'Item del inbox no encontrado.')
        return redirect('events:inbox_admin_dashboard')

    if request.method == 'POST':
        gtd_category = request.POST.get('gtd_category')
        action_type = request.POST.get('action_type')
        priority = request.POST.get('priority', 'media')
        confidence = request.POST.get('confidence', 50)
        notes = request.POST.get('notes', '')

        # Crear o actualizar clasificación
        classification, created = InboxItemClassification.objects.get_or_create(
            inbox_item=inbox_item,
            user=request.user,
            defaults={
                'gtd_category': gtd_category,
                'action_type': action_type,
                'priority': priority,
                'confidence': confidence,
                'notes': notes
            }
        )

        if not created:
            # Actualizar clasificación existente
            classification.gtd_category = gtd_category
            classification.action_type = action_type
            classification.priority = priority
            classification.confidence = confidence
            classification.notes = notes
            classification.save()

        # Registrar en el historial
        InboxItemHistory.objects.create(
            inbox_item=inbox_item,
            user=request.user,
            action='classified',
            old_values=None,
            new_values={
                'gtd_category': gtd_category,
                'action_type': action_type,
                'priority': priority,
                'confidence': confidence
            }
        )

        messages.success(request, f'Clasificación guardada para "{inbox_item.title}"')
        return redirect('events:inbox_item_detail_admin', item_id=item_id)

    # GET request - mostrar formulario
    context = {
        'title': f'Clasificar: {inbox_item.title}',
        'inbox_item': inbox_item,
    }

    return render(request, 'events/classify_inbox_item_admin.html', context)

@login_required
def authorize_inbox_item(request, item_id):
    """
    Vista para autorizar usuarios a ver/clasificar un item del inbox
    """
    # Verificar permisos
    if not (hasattr(request.user, 'cv') and hasattr(request.user.cv, 'role') and request.user.cv.role in ['SU', 'ADMIN', 'GTD_ANALYST']):
        messages.error(request, 'No tienes permisos para autorizar usuarios.')
        return redirect('events:inbox_admin_dashboard')

    try:
        inbox_item = InboxItem.objects.get(id=item_id)
    except InboxItem.DoesNotExist:
        messages.error(request, 'Item del inbox no encontrado.')
        return redirect('events:inbox_admin_dashboard')

    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        permission_level = request.POST.get('permission_level', 'classify')

        try:
            user = User.objects.get(id=user_id)

            # Crear autorización
            authorization, created = InboxItemAuthorization.objects.get_or_create(
                inbox_item=inbox_item,
                user=user,
                defaults={
                    'granted_by': request.user,
                    'permission_level': permission_level
                }
            )

            if not created:
                authorization.permission_level = permission_level
                authorization.granted_by = request.user
                authorization.save()

            # Registrar en el historial
            InboxItemHistory.objects.create(
                inbox_item=inbox_item,
                user=request.user,
                action='authorized',
                old_values=None,
                new_values={
                    'authorized_user': user.username,
                    'permission_level': permission_level
                }
            )

            messages.success(request, f'Autorización actualizada para {user.username}')
            return redirect('events:inbox_item_detail_admin', item_id=item_id)

        except User.DoesNotExist:
            messages.error(request, 'Usuario no encontrado.')

    # GET request - mostrar formulario
    context = {
        'title': f'Autorizar Usuarios: {inbox_item.title}',
        'inbox_item': inbox_item,
    }

    return render(request, 'events/authorize_inbox_item.html', context)

@login_required
def inbox_admin_bulk_action(request):
    """
    Vista para acciones masivas en items del inbox
    """
    # Verificar permisos
    if not (hasattr(request.user, 'cv') and hasattr(request.user.cv, 'role') and request.user.cv.role in ['SU', 'ADMIN', 'GTD_ANALYST']):
        return JsonResponse({'success': False, 'error': 'No tienes permisos para realizar acciones masivas.'})

    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'})

    action = request.POST.get('action')
    selected_items = request.POST.getlist('selected_items')

    if not selected_items:
        return JsonResponse({'success': False, 'error': 'No se seleccionaron items.'})

    items = InboxItem.objects.filter(id__in=selected_items)

    try:
        if action == 'make_public':
            count = items.update(is_public=True)
            return JsonResponse({
                'success': True,
                'message': f'Se hicieron públicos {count} item(s).',
                'count': count
            })

        elif action == 'make_private':
            count = items.update(is_public=False)
            return JsonResponse({
                'success': True,
                'message': f'Se hicieron privados {count} item(s).',
                'count': count
            })

        elif action == 'mark_processed':
            count = 0
            for item in items:
                if not item.is_processed:
                    item.is_processed = True
                    item.processed_at = timezone.now()
                    item.save()
                    count += 1
            return JsonResponse({
                'success': True,
                'message': f'Se marcaron como procesados {count} item(s).',
                'count': count
            })

        elif action == 'delete':
            count = items.count()
            items.delete()
            return JsonResponse({
                'success': True,
                'message': f'Se eliminaron {count} item(s).',
                'count': count
            })

        else:
            return JsonResponse({'success': False, 'error': 'Acción no válida.'})

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error al procesar la acción: {str(e)}'
        })

# ============================================================================
# API ENDPOINTS PARA VINCULACIÓN
# ============================================================================

@login_required
def get_available_tasks(request):
    """
    API endpoint para obtener tareas disponibles para vincular con items del inbox
    """
    if request.method != 'GET':
        return JsonResponse({'success': False, 'error': 'Método no permitido'})

    try:
        search_term = request.GET.get('search', '').strip()

        # Obtener tareas del usuario
        user_tasks = Task.objects.filter(
            Q(host=request.user) | Q(assigned_to=request.user)
        ).select_related('task_status', 'project').order_by('-updated_at')

        # Filtrar por término de búsqueda si se proporciona
        if search_term:
            user_tasks = user_tasks.filter(
                Q(title__icontains=search_term) |
                Q(description__icontains=search_term) |
                Q(project__title__icontains=search_term)
            )

        # Limitar resultados para mejor rendimiento
        user_tasks = user_tasks[:50]

        tasks_data = []
        for task in user_tasks:
            tasks_data.append({
                'id': task.id,
                'title': task.title,
                'description': task.description[:100] + '...' if task.description and len(task.description) > 100 else task.description,
                'status': task.task_status.status_name,
                'status_color': task.task_status.color,
                'project': task.project.title if task.project else 'Sin proyecto',
                'project_id': task.project.id if task.project else None,
                'updated_at': task.updated_at.strftime('%d/%m/%Y %H:%M'),
                'important': task.important
            })

        return JsonResponse({
            'success': True,
            'tasks': tasks_data,
            'total': len(tasks_data)
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@login_required
def get_available_projects(request):
    """
    API endpoint para obtener proyectos disponibles para vincular con items del inbox
    """
    if request.method != 'GET':
        return JsonResponse({'success': False, 'error': 'Método no permitido'})

    try:
        search_term = request.GET.get('search', '').strip()

        # Obtener proyectos del usuario
        user_projects = Project.objects.filter(
            Q(host=request.user) | Q(assigned_to=request.user) | Q(attendees=request.user)
        ).distinct().select_related('project_status', 'event').order_by('-updated_at')

        # Filtrar por término de búsqueda si se proporciona
        if search_term:
            user_projects = user_projects.filter(
                Q(title__icontains=search_term) |
                Q(description__icontains=search_term) |
                Q(event__title__icontains=search_term)
            )

        # Limitar resultados para mejor rendimiento
        user_projects = user_projects[:50]

        projects_data = []
        for project in user_projects:
            projects_data.append({
                'id': project.id,
                'title': project.title,
                'description': project.description[:100] + '...' if project.description and len(project.description) > 100 else project.description,
                'status': project.project_status.status_name,
                'status_color': project.project_status.color,
                'event': project.event.title if project.event else 'Sin evento',
                'event_id': project.event.id if project.event else None,
                'task_count': project.task_set.count(),
                'updated_at': project.updated_at.strftime('%d/%m/%Y %H:%M'),
                'important': getattr(project, 'important', False)  # Si el proyecto tiene campo importante
            })

        return JsonResponse({
            'success': True,
            'projects': projects_data,
            'total': len(projects_data)
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

# ============================================================================
# PANEL DE GESTIÓN GTD - ANALISTA
# ============================================================================

@login_required
def inbox_management_panel(request):
    """
    Panel de gestión del analista GTD - Control de interacciones y configuraciones
    """
    # Verificar permisos - solo superusers o administradores con rol GTD
    if not (request.user.is_superuser or
            (hasattr(request.user, 'cv') and hasattr(request.user.cv, 'role') and
             request.user.cv.role in ['SU', 'ADMIN', 'GTD_ANALYST'])):
        messages.error(request, 'No tienes permisos para acceder al panel de gestión GTD.')
        return redirect('events:inbox')

    # Obtener estadísticas generales
    total_inbox_items = InboxItem.objects.count()
    processed_items = InboxItem.objects.filter(is_processed=True).count()
    unprocessed_items = InboxItem.objects.filter(is_processed=False).count()
    public_items = InboxItem.objects.filter(is_public=True).count()

    # Estadísticas por tipo de interacción (basado en context o descripción)
    email_items = InboxItem.objects.filter(
        models.Q(description__icontains='@') |
        models.Q(context__icontains='email')
    ).count()

    call_items = InboxItem.objects.filter(
        models.Q(title__icontains='llamada') |
        models.Q(title__icontains='call') |
        models.Q(context__icontains='telefono')
    ).count()

    chat_items = InboxItem.objects.filter(
        models.Q(title__icontains='chat') |
        models.Q(context__icontains='chat')
    ).count()

    # Items por prioridad
    high_priority = InboxItem.objects.filter(priority='alta', is_processed=False).count()
    medium_priority = InboxItem.objects.filter(priority='media', is_processed=False).count()
    low_priority = InboxItem.objects.filter(priority='baja', is_processed=False).count()

    # Items recientes para las colas
    recent_emails = InboxItem.objects.filter(
        models.Q(description__icontains='@') |
        models.Q(context__icontains='email'),
        is_processed=False
    ).select_related('created_by').order_by('-created_at')[:10]

    recent_calls = InboxItem.objects.filter(
        models.Q(title__icontains='llamada') |
        models.Q(title__icontains='call'),
        is_processed=False
    ).select_related('created_by').order_by('-created_at')[:10]

    recent_chats = InboxItem.objects.filter(
        models.Q(title__icontains='chat'),
        is_processed=False
    ).select_related('created_by').order_by('-created_at')[:10]

    # Obtener configuraciones actuales desde la base de datos
    settings_obj = GTDProcessingSettings.get_active_settings()
    if settings_obj:
        processing_settings = {
            'auto_email_processing': settings_obj.auto_email_processing,
            'auto_call_queue': settings_obj.auto_call_queue,
            'auto_chat_routing': settings_obj.auto_chat_routing,
            'processing_interval': settings_obj.processing_interval,
            'max_concurrent': settings_obj.max_concurrent_items,
            'email_batch_size': settings_obj.email_batch_size,
            'call_queue_timeout': settings_obj.call_queue_timeout,
            'chat_response_timeout': settings_obj.chat_response_timeout,
            'enable_bot_cx': settings_obj.enable_bot_cx,
            'enable_bot_atc': settings_obj.enable_bot_atc,
            'enable_human_agents': settings_obj.enable_human_agents,
        }
    else:
        # Configuraciones por defecto si no existen
        processing_settings = {
            'auto_email_processing': True,
            'auto_call_queue': True,
            'auto_chat_routing': True,
            'processing_interval': 60,
            'max_concurrent': 5,
            'email_batch_size': 10,
            'call_queue_timeout': 30,
            'chat_response_timeout': 300,
            'enable_bot_cx': True,
            'enable_bot_atc': True,
            'enable_human_agents': True,
        }

    context = {
        'title': 'Panel de Gestión GTD - Analista',
        'stats': {
            'total': total_inbox_items,
            'processed': processed_items,
            'unprocessed': unprocessed_items,
            'public': public_items,
            'emails': email_items,
            'calls': call_items,
            'chats': chat_items,
            'high_priority': high_priority,
            'medium_priority': medium_priority,
            'low_priority': low_priority,
        },
        'recent_emails': recent_emails,
        'recent_calls': recent_calls,
        'recent_chats': recent_chats,
        'processing_settings': processing_settings,
    }

    return render(request, 'events/inbox_management_panel.html', context)

@login_required
def update_processing_settings(request):
    """
    API endpoint para actualizar configuraciones de procesamiento
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'})

    # Verificar permisos
    if not (hasattr(request.user, 'cv') and hasattr(request.user.cv, 'role') and
            request.user.cv.role in ['SU', 'ADMIN', 'GTD_ANALYST']):
        return JsonResponse({'success': False, 'error': 'No tienes permisos'})

    try:
        # Obtener o crear configuración para el usuario
        settings_obj, created = GTDProcessingSettings.objects.get_or_create(
            created_by=request.user,
            defaults={'is_active': True}
        )

        # Actualizar configuraciones
        settings_obj.auto_email_processing = request.POST.get('auto_email_processing') == 'true'
        settings_obj.auto_call_queue = request.POST.get('auto_call_queue') == 'true'
        settings_obj.auto_chat_routing = request.POST.get('auto_chat_routing') == 'true'
        settings_obj.processing_interval = int(request.POST.get('processing_interval', 60))
        settings_obj.max_concurrent_items = int(request.POST.get('max_concurrent', 5))

        # Guardar configuración
        settings_obj.save()

        return JsonResponse({
            'success': True,
            'message': 'Configuraciones actualizadas exitosamente',
            'created': created
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

# ============================================================================
# ENDPOINTS DE API PARA COLAS
# ============================================================================

@login_required
def get_queue_data(request):
    """
    API endpoint para obtener datos de las colas en tiempo real
    """
    if request.method != 'GET':
        return JsonResponse({'success': False, 'error': 'Método no permitido'})

    try:
        # Estadísticas en tiempo real
        active_items = InboxItem.objects.filter(is_processed=False).count()
        pending_items = InboxItem.objects.filter(
            is_processed=False,
            created_at__gte=timezone.now() - timedelta(hours=1)
        ).count()

        # Conteo por tipo mejorado
        emails = InboxItem.objects.filter(
            models.Q(description__icontains='@') |
            models.Q(context__icontains='email') |
            models.Q(title__icontains='email'),
            is_processed=False
        ).count()

        calls = InboxItem.objects.filter(
            models.Q(title__icontains='llamada') |
            models.Q(title__icontains='call') |
            models.Q(context__icontains='telefono') |
            models.Q(context__icontains='phone'),
            is_processed=False
        ).count()

        chats = InboxItem.objects.filter(
            models.Q(title__icontains='chat') |
            models.Q(context__icontains='chat') |
            models.Q(title__icontains='mensaje'),
            is_processed=False
        ).count()

        return JsonResponse({
            'success': True,
            'data': {
                'active': active_items,
                'pending': pending_items,
                'emails': emails,
                'calls': calls,
                'chats': chats
            }
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@login_required
def get_email_queue_items(request):
    """
    API endpoint para obtener items de la cola de emails
    """
    if request.method != 'GET':
        return JsonResponse({'success': False, 'error': 'Método no permitido'})

    try:
        # Obtener items de email no procesados
        email_items = InboxItem.objects.filter(
            models.Q(description__icontains='@') |
            models.Q(context__icontains='email') |
            models.Q(title__icontains='email'),
            is_processed=False
        ).select_related('created_by', 'assigned_to').order_by('-created_at')[:20]  # Limitar a 20 para rendimiento

        items_data = []
        for item in email_items:
            # Calcular tiempo transcurrido
            time_diff = timezone.now() - item.created_at
            if time_diff.days > 0:
                time_ago = f"{time_diff.days}d ago"
            elif time_diff.seconds // 3600 > 0:
                time_ago = f"{time_diff.seconds // 3600}h ago"
            elif time_diff.seconds // 60 > 0:
                time_ago = f"{time_diff.seconds // 60}m ago"
            else:
                time_ago = "Just now"

            items_data.append({
                'id': item.id,
                'title': item.title[:50] + ('...' if len(item.title) > 50 else ''),
                'sender': item.created_by.username if item.created_by else 'Unknown',
                'priority': item.priority,
                'time': time_ago,
                'status': 'pending' if not item.assigned_to else 'assigned',
                'assigned_to': item.assigned_to.username if item.assigned_to else None
            })

        return JsonResponse({
            'success': True,
            'data': items_data
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@login_required
def get_call_queue_items(request):
    """
    API endpoint para obtener items de la cola de llamadas
    """
    if request.method != 'GET':
        return JsonResponse({'success': False, 'error': 'Método no permitido'})

    try:
        # Obtener items de llamadas no procesados
        call_items = InboxItem.objects.filter(
            models.Q(title__icontains='llamada') |
            models.Q(title__icontains='call') |
            models.Q(context__icontains='telefono') |
            models.Q(context__icontains='phone'),
            is_processed=False
        ).select_related('created_by', 'assigned_to').order_by('-created_at')[:20]

        items_data = []
        for item in call_items:
            # Calcular tiempo transcurrido
            time_diff = timezone.now() - item.created_at
            if time_diff.days > 0:
                time_ago = f"{time_diff.days}d ago"
            elif time_diff.seconds // 3600 > 0:
                time_ago = f"{time_diff.seconds // 3600}h ago"
            elif time_diff.seconds // 60 > 0:
                time_ago = f"{time_diff.seconds // 60}m ago"
            else:
                time_ago = "Just now"

            # Calcular tiempo de espera (simulado)
            wait_minutes = min(time_diff.seconds // 60, 60)  # Máximo 60 minutos para display

            items_data.append({
                'id': item.id,
                'title': item.title[:50] + ('...' if len(item.title) > 50 else ''),
                'caller': item.created_by.username if item.created_by else 'Unknown',
                'priority': item.priority,
                'time': time_ago,
                'status': 'pending' if not item.assigned_to else 'assigned',
                'waitTime': f"{wait_minutes:02d}:{(time_diff.seconds % 60):02d}",
                'assigned_to': item.assigned_to.username if item.assigned_to else None
            })

        return JsonResponse({
            'success': True,
            'data': items_data
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@login_required
def get_chat_queue_items(request):
    """
    API endpoint para obtener items de la cola de chats
    """
    if request.method != 'GET':
        return JsonResponse({'success': False, 'error': 'Método no permitido'})

    try:
        # Obtener items de chat no procesados
        chat_items = InboxItem.objects.filter(
            models.Q(title__icontains='chat') |
            models.Q(context__icontains='chat') |
            models.Q(title__icontains='mensaje'),
            is_processed=False
        ).select_related('created_by', 'assigned_to').order_by('-created_at')[:20]

        items_data = []
        for item in chat_items:
            # Calcular tiempo transcurrido
            time_diff = timezone.now() - item.created_at
            if time_diff.days > 0:
                time_ago = f"{time_diff.days}d ago"
            elif time_diff.seconds // 3600 > 0:
                time_ago = f"{time_diff.seconds // 3600}h ago"
            elif time_diff.seconds // 60 > 0:
                time_ago = f"{time_diff.seconds // 60}m ago"
            else:
                time_ago = "Just now"

            # Contar mensajes (simulado basado en contexto)
            messages_count = 1
            if item.context:
                try:
                    context_data = json.loads(item.context) if isinstance(item.context, str) else item.context
                    if isinstance(context_data, dict) and 'messages' in context_data:
                        messages_count = len(context_data['messages'])
                except:
                    messages_count = 1

            items_data.append({
                'id': item.id,
                'title': item.title[:50] + ('...' if len(item.title) > 50 else ''),
                'customer': item.created_by.username if item.created_by else 'Unknown',
                'priority': item.priority,
                'time': time_ago,
                'status': 'active' if item.assigned_to else 'pending',
                'messages': messages_count,
                'assigned_to': item.assigned_to.username if item.assigned_to else None
            })

        return JsonResponse({
            'success': True,
            'data': items_data
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@login_required
def process_queue(request):
    """
    API endpoint para procesar colas automáticamente
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'})

    try:
        data = json.loads(request.body)
        queue_type = data.get('queue_type')
        action = data.get('action')

        if not queue_type or not action:
            return JsonResponse({'success': False, 'error': 'Parámetros requeridos faltantes'})

        processed_count = 0
        activated_count = 0

        # Definir filtros por tipo de cola
        queue_filters = {
            'email': models.Q(description__icontains='@') |
                    models.Q(context__icontains='email') |
                    models.Q(title__icontains='email'),
            'call': models.Q(title__icontains='llamada') |
                   models.Q(title__icontains='call') |
                   models.Q(context__icontains='telefono') |
                   models.Q(context__icontains='phone'),
            'chat': models.Q(title__icontains='chat') |
                   models.Q(context__icontains='chat') |
                   models.Q(title__icontains='mensaje')
        }

        if queue_type not in queue_filters:
            return JsonResponse({'success': False, 'error': 'Tipo de cola no válido'})

        # Obtener items no procesados de la cola específica
        queue_items = InboxItem.objects.filter(
            queue_filters[queue_type],
            is_processed=False,
            assigned_to__isnull=True  # Solo items no asignados
        )

        if action == 'process':
            # Asignar automáticamente agentes a los items
            for item in queue_items:
                if item.assign_to_available_user():
                    processed_count += 1

        elif action == 'activate':
            # Para llamadas: marcar como activas y asignar
            for item in queue_items:
                if item.assign_to_available_user():
                    activated_count += 1

        elif action == 'pause':
            # Para pausar: no hacer nada específico por ahora
            pass

        else:
            return JsonResponse({'success': False, 'error': 'Acción no válida'})

        return JsonResponse({
            'success': True,
            'processed_count': processed_count,
            'activated_count': activated_count,
            'message': f'Cola {queue_type} procesada exitosamente'
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

# ============================================================================
# GESTIÓN DE INTERACCIONES
# ============================================================================

@login_required
def assign_interaction_to_agent(request):
    """
    API endpoint para asignar una interacción a un agente/bot
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'})

    try:
        interaction_id = request.POST.get('interaction_id')
        agent_type = request.POST.get('agent_type')  # 'bot-cx', 'bot-atc', 'human-*'
        priority = request.POST.get('priority', 'media')
        notes = request.POST.get('notes', '')

        if not interaction_id or not agent_type:
            return JsonResponse({'success': False, 'error': 'Datos incompletos'})

        # Obtener el InboxItem
        inbox_item = InboxItem.objects.get(id=interaction_id)

        # Verificar permisos
        if not (request.user == inbox_item.created_by or
                inbox_item.authorized_users.filter(id=request.user.id).exists() or
                (hasattr(request.user, 'cv') and hasattr(request.user.cv, 'role') and
                 request.user.cv.role in ['SU', 'ADMIN', 'GTD_ANALYST'])):
            return JsonResponse({'success': False, 'error': 'No tienes permisos para asignar esta interacción'})

        # Actualizar el InboxItem
        inbox_item.priority = priority
        if notes:
            inbox_item.notes = notes

        # Agregar información de asignación en context
        context_data = inbox_item.context or {}
        if isinstance(context_data, str):
            # Si es string, convertir a dict
            try:
                context_data = json.loads(context_data)
            except:
                context_data = {}
        context_data.update({
            'assigned_to': agent_type,
            'assigned_by': request.user.username,
            'assigned_at': timezone.now().isoformat(),
            'assignment_notes': notes
        })
        inbox_item.context = context_data
        inbox_item.save()

        # Registrar en historial
        InboxItemHistory.objects.create(
            inbox_item=inbox_item,
            user=request.user,
            action='assigned',
            new_values={
                'assigned_to': agent_type,
                'priority': priority,
                'notes': notes
            }
        )

        return JsonResponse({
            'success': True,
            'message': f'Interacción asignada a {agent_type} exitosamente'
        })

    except InboxItem.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Interacción no encontrada'})
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@login_required
def mark_interaction_resolved(request):
    """
    API endpoint para marcar una interacción como resuelta
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'})

    try:
        interaction_id = request.POST.get('interaction_id')
        resolution_notes = request.POST.get('resolution_notes', '')

        if not interaction_id:
            return JsonResponse({'success': False, 'error': 'ID de interacción requerido'})

        # Obtener el InboxItem
        inbox_item = InboxItem.objects.get(id=interaction_id)

        # Verificar permisos
        if not (request.user == inbox_item.created_by or
                inbox_item.authorized_users.filter(id=request.user.id).exists() or
                (hasattr(request.user, 'cv') and hasattr(request.user.cv, 'role') and
                 request.user.cv.role in ['SU', 'ADMIN', 'GTD_ANALYST'])):
            return JsonResponse({'success': False, 'error': 'No tienes permisos para resolver esta interacción'})

        # Marcar como procesada
        inbox_item.is_processed = True
        inbox_item.processed_at = timezone.now()

        # Agregar notas de resolución
        if resolution_notes:
            context_data = inbox_item.context or {}
            if isinstance(context_data, str):
                # Si es string, convertir a dict
                try:
                    context_data = json.loads(context_data)
                except:
                    context_data = {}
            context_data['resolution_notes'] = resolution_notes
            context_data['resolved_by'] = request.user.username
            context_data['resolved_at'] = timezone.now().isoformat()
            inbox_item.context = context_data

        inbox_item.save()

        # Registrar en historial
        InboxItemHistory.objects.create(
            inbox_item=inbox_item,
            user=request.user,
            action='resolved',
            new_values={
                'resolution_notes': resolution_notes,
                'processed_at': inbox_item.processed_at.isoformat()
            }
        )

        return JsonResponse({
            'success': True,
            'message': 'Interacción marcada como resuelta'
        })

    except InboxItem.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Interacción no encontrada'})
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@login_required
def assign_inbox_item_api(request):
    """
    API endpoint para asignar manualmente un item del inbox a un usuario
    Solo para administradores
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'})

    # Verificar permisos de administrador
    if not (hasattr(request.user, 'cv') and hasattr(request.user.cv, 'role') and
            request.user.cv.role in ['SU', 'ADMIN', 'GTD_ANALYST']):
        return JsonResponse({'success': False, 'error': 'No tienes permisos para asignar items'})

    try:
        item_id = request.POST.get('item_id')
        user_id = request.POST.get('user_id')

        if not item_id or not user_id:
            return JsonResponse({'success': False, 'error': 'ID de item y usuario requeridos'})

        # Obtener el item y usuario
        inbox_item = InboxItem.objects.get(id=item_id)
        target_user = User.objects.get(id=user_id)

        # Verificar que el usuario objetivo esté activo
        if not target_user.is_active:
            return JsonResponse({'success': False, 'error': 'El usuario objetivo no está activo'})

        # Asignar el item
        old_assigned = inbox_item.assigned_to
        inbox_item.assigned_to = target_user
        inbox_item.save(update_fields=['assigned_to'])

        # Registrar en historial
        InboxItemHistory.objects.create(
            inbox_item=inbox_item,
            user=request.user,
            action='manual_assigned',
            old_values={'assigned_to': old_assigned.username if old_assigned else None},
            new_values={
                'assigned_to': target_user.username,
                'assignment_method': 'manual',
                'assigned_by': request.user.username
            }
        )

        return JsonResponse({
            'success': True,
            'message': f'Item asignado a {target_user.username} exitosamente'
        })

    except InboxItem.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Item del inbox no encontrado'})
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Usuario no encontrado'})
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@login_required
def create_inbox_item_api(request):
    """
    API endpoint para crear un nuevo item del inbox desde el panel root
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'})

    try:
        # Obtener datos del formulario
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        gtd_category = request.POST.get('gtd_category', 'pendiente')
        priority = request.POST.get('priority', 'media')
        action_type = request.POST.get('action_type', '')
        context = request.POST.get('context', '').strip()
        auto_assign = request.POST.get('auto_assign', 'false').lower() == 'true'

        # Validar datos requeridos
        if not title:
            return JsonResponse({'success': False, 'error': 'El título es requerido'})

        # Crear el item del inbox
        inbox_item = InboxItem.objects.create(
            title=title,
            description=description,
            created_by=request.user,
            gtd_category=gtd_category,
            priority=priority,
            action_type=action_type if action_type else None,
            context=context
        )

        # Asignación automática si se solicita
        if auto_assign:
            inbox_item.assign_to_available_user()

        # Registrar en historial
        InboxItemHistory.objects.create(
            inbox_item=inbox_item,
            user=request.user,
            action='created',
            new_values={
                'title': title,
                'description': description,
                'gtd_category': gtd_category,
                'priority': priority,
                'action_type': action_type,
                'context': context,
                'auto_assigned': auto_assign
            }
        )

        return JsonResponse({
            'success': True,
            'message': f'Item "{title}" creado exitosamente',
            'item_id': inbox_item.id,
            'assigned_to': inbox_item.assigned_to.username if inbox_item.assigned_to else None
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


# En gtd_views.py, agregar:

@login_required
def inbox_link_checker(request):
    """
    Vista para verificar y corregir enlaces de items del inbox
    """
    # Verificar permisos
    if not (hasattr(request.user, 'cv') and hasattr(request.user.cv, 'role') and 
            request.user.cv.role in ['SU', 'ADMIN', 'GTD_ANALYST']):
        messages.error(request, 'No tienes permisos para acceder a esta herramienta.')
        return redirect('events:inbox')
    
    action = request.GET.get('action', '')
    
    if action == 'verify':
        from .gtd_utils import verify_inbox_links
        issues = verify_inbox_links()
        context = {
            'title': 'Verificador de Enlaces del Inbox',
            'issues': issues,
            'total_issues': len(issues),
            'action': 'verify'
        }
        return render(request, 'events/inbox_link_checker.html', context)
    
    elif action == 'fix':
        from .gtd_utils import fix_broken_links
        result = fix_broken_links()
        context = {
            'title': 'Corrector de Enlaces del Inbox',
            'result': result,
            'action': 'fix'
        }
        return render(request, 'events/inbox_link_checker.html', context)
    
    # Vista principal
    context = {
        'title': 'Herramienta de Verificación de Enlaces',
        'action': 'menu'
    }
    return render(request, 'events/inbox_link_checker.html', context)
    
@login_required
def classify_inbox_item_ajax(request, item_id):
    """
    Vista AJAX para clasificar items del inbox
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'})
    
    try:
        inbox_item = get_object_or_404(InboxItem, id=item_id)
        
        # Verificar permisos
        if not (request.user == inbox_item.created_by or
                inbox_item.authorized_users.filter(id=request.user.id).exists() or
                (hasattr(request.user, 'cv') and hasattr(request.user.cv, 'role') and
                 request.user.cv.role in ['SU', 'ADMIN', 'GTD_ANALYST'])):
            return JsonResponse({'success': False, 'error': 'No tienes permisos para clasificar este item'})
        
        # Obtener valores actuales para comparar
        old_values = {
            'gtd_category': inbox_item.gtd_category,
            'action_type': inbox_item.action_type,
            'priority': inbox_item.priority
        }
        
        # Actualizar item
        gtd_category = request.POST.get('gtd_category')
        action_type = request.POST.get('action_type')
        priority = request.POST.get('priority', 'media')
        confidence = request.POST.get('confidence', 80)
        notes = request.POST.get('notes', '')
        
        # Validar que la categoría sea válida
        valid_categories = ['pendiente', 'accionable', 'no_accionable']
        if gtd_category and gtd_category in valid_categories:
            inbox_item.gtd_category = gtd_category
        
        # Validar tipo de acción
        valid_actions = ['hacer', 'delegar', 'posponer', 'proyecto', 'eliminar', 'archivar', 'incubar', '']
        if action_type in valid_actions:
            inbox_item.action_type = action_type if action_type else None
        
        # Validar prioridad
        valid_priorities = ['baja', 'media', 'alta']
        if priority in valid_priorities:
            inbox_item.priority = priority
        
        # Guardar confianza y notas si existen en el modelo
        if hasattr(inbox_item, 'classification_confidence'):
            inbox_item.classification_confidence = int(confidence)
        if hasattr(inbox_item, 'classification_notes'):
            inbox_item.classification_notes = notes
        
        inbox_item.save()
        
        # Registrar en historial
        new_values = {
            'gtd_category': inbox_item.gtd_category,
            'action_type': inbox_item.action_type,
            'priority': inbox_item.priority,
            'confidence': confidence,
            'notes': notes
        }
        
        # Determinar si hubo cambios significativos
        changed = (
            old_values['gtd_category'] != new_values['gtd_category'] or
            old_values['action_type'] != new_values['action_type'] or
            old_values['priority'] != new_values['priority']
        )
        
        # Crear entrada en historial
        InboxItemHistory.objects.create(
            inbox_item=inbox_item,
            user=request.user,
            action='reclassified' if changed else 'classification_updated',
            old_values=old_values if changed else None,
            new_values=new_values
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Clasificación guardada exitosamente',
            'changed': changed,
            'old_values': old_values,
            'new_values': new_values
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@login_required
def get_classification_history(request, item_id):
    """
    API endpoint para obtener el historial de clasificaciones
    """
    if request.method != 'GET':
        return JsonResponse({'success': False, 'error': 'Método no permitido'})
    
    try:
        inbox_item = get_object_or_404(InboxItem, id=item_id)
        
        # Verificar permisos básicos
        if not (request.user == inbox_item.created_by or
                inbox_item.authorized_users.filter(id=request.user.id).exists() or
                inbox_item.is_public or
                (hasattr(request.user, 'cv') and hasattr(request.user.cv, 'role') and
                 request.user.cv.role in ['SU', 'ADMIN', 'GTD_ANALYST'])):
            return JsonResponse({'success': False, 'error': 'No tienes permisos para ver este historial'})
        
        # Obtener historial de clasificaciones
        history = InboxItemHistory.objects.filter(
            inbox_item=inbox_item,
            action__in=['classified', 'classification_updated', 'reclassified']
        ).select_related('user').order_by('-created_at')[:20]
        
        history_data = []
        for h in history:
            history_data.append({
                'id': h.id,
                'user': h.user.username if h.user else 'Sistema',
                'action': h.action,
                'old_values': h.old_values or {},
                'new_values': h.new_values or {},
                'notes': h.new_values.get('notes', '') if h.new_values else '',
                'created_at': h.created_at.isoformat()
            })
        
        return JsonResponse({
            'success': True,
            'history': history_data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@login_required
def get_consensus_api(request, item_id):
    """
    API endpoint para obtener el consenso de clasificación de un item
    """
    if request.method != 'GET':
        return JsonResponse({'success': False, 'error': 'Método no permitido'})
    
    try:
        inbox_item = get_object_or_404(InboxItem, id=item_id)
        
        # Verificar permisos básicos
        if not (request.user == inbox_item.created_by or
                inbox_item.authorized_users.filter(id=request.user.id).exists() or
                inbox_item.is_public or
                (hasattr(request.user, 'cv') and hasattr(request.user.cv, 'role') and
                 request.user.cv.role in ['SU', 'ADMIN', 'GTD_ANALYST'])):
            return JsonResponse({'success': False, 'error': 'No tienes permisos para ver este item'})
        
        # Obtener clasificaciones
        classifications = InboxItemClassification.objects.filter(inbox_item=inbox_item)
        
        # Calcular consenso usando los métodos del modelo
        consensus_category = inbox_item.get_classification_consensus()
        consensus_action = inbox_item.get_action_type_consensus()
        
        # Si no hay consenso por los métodos del modelo, calcular manualmente
        if not consensus_category and classifications.exists():
            category_votes = {}
            for c in classifications:
                if c.gtd_category:
                    category_votes[c.gtd_category] = category_votes.get(c.gtd_category, 0) + 1
            if category_votes:
                consensus_category = max(category_votes, key=category_votes.get)
        
        if not consensus_action and classifications.exists():
            action_votes = {}
            for c in classifications:
                if c.action_type:
                    action_votes[c.action_type] = action_votes.get(c.action_type, 0) + 1
            if action_votes:
                consensus_action = max(action_votes, key=action_votes.get)
        
        return JsonResponse({
            'success': True,
            'consensus_category': consensus_category,
            'consensus_action': consensus_action,
            'votes': classifications.count()
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })