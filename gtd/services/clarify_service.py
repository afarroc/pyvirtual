"""
Servicio de Clarificación GTD (Etapa 2)
Responsabilidad: Procesar items del inbox y decidir su destino según GTD
"""

import logging
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime, timedelta

from django.db import transaction
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from events.models import InboxItem, InboxItemHistory, Task, Project, Event, TaskStatus, ProjectStatus

User = get_user_model()
logger = logging.getLogger(__name__)


class ClarifyService:
    """
    Servicio de clarificación GTD
    
    El proceso de clarificación responde a dos preguntas clave:
    1. ¿Qué es esto? (Identificar el item)
    2. ¿Cuál es la siguiente acción? (Decidir qué hacer)
    
    Decisiones GTD:
    - Si NO es accionable: Archivar, Eliminar o Incubar (Algún día/Quizás)
    - Si ES accionable:
        - Si toma < 2 minutos: HACERLO AHORA
        - Si toma > 2 minutos: Delegar, Posponer o Convertir en Proyecto
    """
    
    # Categorías GTD
    CATEGORY_ACCIONABLE = 'accionable'
    CATEGORY_NO_ACCIONABLE = 'no_accionable'
    CATEGORY_PENDIENTE = 'pendiente'
    
    # Tipos de acción
    ACTION_DO = 'hacer'
    ACTION_DELEGATE = 'delegar'
    ACTION_DEFER = 'posponer'
    ACTION_PROJECT = 'proyecto'
    ACTION_DELETE = 'eliminar'
    ACTION_ARCHIVE = 'archivar'
    ACTION_SOMEDAY = 'incubar'
    ACTION_WAIT = 'esperar'
    
    # Tiempo mínimo para considerar "hacer ahora" (2 minutos en segundos)
    DO_NOW_THRESHOLD = 120
    
    def __init__(self, user):
        self.user = user
        self.logger = logging.getLogger(__name__)
    
    def clarify_item(self, item_id: int, decision_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Procesa un item del inbox aplicando el flujo GTD
        """
        try:
            item = InboxItem.objects.get(
                id=item_id,
                created_by=self.user
            )
        except InboxItem.DoesNotExist:
            return {'success': False, 'error': 'Item no encontrado'}
        
        if item.is_processed:
            return {'success': False, 'error': 'Este item ya fue procesado'}
        
        gtd_category = decision_data.get('gtd_category')
        action_type = decision_data.get('action_type')
        
        if not self._validate_decision(gtd_category, action_type):
            return {'success': False, 'error': 'Decisión inválida'}
        
        with transaction.atomic():
            if gtd_category == self.CATEGORY_NO_ACCIONABLE:
                return self._handle_no_accionable(item, action_type, decision_data)
            else:
                return self._handle_accionable(item, action_type, decision_data)
    
    def _validate_decision(self, gtd_category: str, action_type: str) -> bool:
        valid_categories = [
            self.CATEGORY_ACCIONABLE,
            self.CATEGORY_NO_ACCIONABLE,
            self.CATEGORY_PENDIENTE
        ]
        
        valid_actions = [
            self.ACTION_DO, self.ACTION_DELEGATE, self.ACTION_DEFER,
            self.ACTION_PROJECT, self.ACTION_DELETE, self.ACTION_ARCHIVE,
            self.ACTION_SOMEDAY, self.ACTION_WAIT
        ]
        
        if gtd_category not in valid_categories:
            return False
        
        if action_type and action_type not in valid_actions:
            return False
        
        if gtd_category == self.CATEGORY_NO_ACCIONABLE and action_type in [
            self.ACTION_DO, self.ACTION_DELEGATE, self.ACTION_DEFER, self.ACTION_PROJECT
        ]:
            return False
        
        return True
    
    def _handle_no_accionable(self, item: InboxItem, action_type: str, decision_data: Dict[str, Any]) -> Dict[str, Any]:
        result = {'success': True, 'action': action_type}
        
        if action_type == self.ACTION_DELETE:
            title = item.title
            item.delete()
            result['message'] = f'Item "{title}" eliminado'
            
        elif action_type == self.ACTION_ARCHIVE:
            item.gtd_category = self.CATEGORY_NO_ACCIONABLE
            item.action_type = self.ACTION_ARCHIVE
            item.save()
            self._log_action(item, 'archived', {'reference': True})
            result['message'] = f'Item "{item.title}" archivado como referencia'
            
        elif action_type == self.ACTION_SOMEDAY:
            item.gtd_category = self.CATEGORY_NO_ACCIONABLE
            item.action_type = self.ACTION_SOMEDAY
            item.save()
            self._log_action(item, 'someday', {'future': True})
            result['message'] = f'Item "{item.title}" guardado para "Algún día / Quizás"'
            
        elif action_type == self.ACTION_WAIT:
            item.gtd_category = self.CATEGORY_NO_ACCIONABLE
            item.action_type = self.ACTION_WAIT
            item.save()
            self._log_action(item, 'waiting', {'waiting_for': decision_data.get('waiting_for', 'información')})
            result['message'] = f'Item "{item.title}" en espera de información'
        
        else:
            item.gtd_category = self.CATEGORY_NO_ACCIONABLE
            item.save()
            result['message'] = f'Item "{item.title}" categorizado como no accionable'
        
        return result
    
    def _handle_accionable(self, item: InboxItem, action_type: str, decision_data: Dict[str, Any]) -> Dict[str, Any]:
        result = {'success': True, 'action': action_type}
        
        estimated_time = decision_data.get('estimated_time', 0)
        
        if action_type == self.ACTION_DO or (estimated_time and estimated_time <= self.DO_NOW_THRESHOLD):
            return self._handle_do_now(item, decision_data)
        
        if action_type == self.ACTION_DELEGATE:
            return self._handle_delegate(item, decision_data)
        
        if action_type == self.ACTION_DEFER:
            return self._handle_defer(item, decision_data)
        
        if action_type == self.ACTION_PROJECT:
            return self._handle_project(item, decision_data)
        
        return self._handle_default_task(item, decision_data)
    
    def _handle_do_now(self, item: InboxItem, data: Dict[str, Any]) -> Dict[str, Any]:
        from events.management.task_manager import TaskManager
        task_manager = TaskManager(self.user)
        
        task = task_manager.create_task(
            title=item.title,
            description=item.description or 'Tarea completada en 2 minutos (GTD)',
            important=data.get('important', False),
            assigned_to=self.user
        )
        
        task_status = TaskStatus.objects.get(status_name='Completed')
        task.task_status = task_status
        task.save()
        
        item.is_processed = True
        item.processed_at = timezone.now()
        item.gtd_category = self.CATEGORY_ACCIONABLE
        item.action_type = self.ACTION_DO
        
        content_type = ContentType.objects.get_for_model(task)
        item.processed_to_content_type = content_type
        item.processed_to_object_id = task.id
        item.save()
        
        self._log_action(item, 'done_now', {'task_id': task.id})
        
        return {
            'success': True,
            'action': self.ACTION_DO,
            'message': f'Tarea "{item.title}" completada (regla de 2 minutos)',
            'task_id': task.id
        }
    
    def _handle_delegate(self, item: InboxItem, data: Dict[str, Any]) -> Dict[str, Any]:
        assigned_to_id = data.get('assigned_to_id')
        if not assigned_to_id:
            return {'success': False, 'error': 'Se requiere un usuario para delegar'}
        
        try:
            assigned_to = User.objects.get(id=assigned_to_id)
        except User.DoesNotExist:
            return {'success': False, 'error': 'Usuario no encontrado'}
        
        from events.management.task_manager import TaskManager
        task_manager = TaskManager(self.user)
        
        task = task_manager.create_task(
            title=item.title,
            description=item.description or f'Delegado por {self.user.username}',
            important=data.get('important', False),
            assigned_to=assigned_to,
            due_date=data.get('due_date')
        )
        
        item.is_processed = True
        item.processed_at = timezone.now()
        item.gtd_category = self.CATEGORY_ACCIONABLE
        item.action_type = self.ACTION_DELEGATE
        
        content_type = ContentType.objects.get_for_model(task)
        item.processed_to_content_type = content_type
        item.processed_to_object_id = task.id
        item.save()
        
        self._log_action(item, 'delegated', {
            'task_id': task.id,
            'assigned_to': assigned_to.username
        })
        
        return {
            'success': True,
            'action': self.ACTION_DELEGATE,
            'message': f'Tarea "{item.title}" delegada a {assigned_to.username}',
            'task_id': task.id
        }
    
    def _handle_defer(self, item: InboxItem, data: Dict[str, Any]) -> Dict[str, Any]:
        from events.management.task_manager import TaskManager
        task_manager = TaskManager(self.user)
        
        task = task_manager.create_task(
            title=item.title,
            description=item.description,
            important=data.get('important', False),
            assigned_to=self.user,
            due_date=data.get('due_date')
        )
        
        if data.get('start_date'):
            task_status = TaskStatus.objects.get(status_name='Pending')
            task.task_status = task_status
            task.save()
        
        item.is_processed = True
        item.processed_at = timezone.now()
        item.gtd_category = self.CATEGORY_ACCIONABLE
        item.action_type = self.ACTION_DEFER
        
        content_type = ContentType.objects.get_for_model(task)
        item.processed_to_content_type = content_type
        item.processed_to_object_id = task.id
        item.save()
        
        self._log_action(item, 'deferred', {
            'task_id': task.id,
            'due_date': str(data.get('due_date')) if data.get('due_date') else None
        })
        
        return {
            'success': True,
            'action': self.ACTION_DEFER,
            'message': f'Tarea "{item.title}" aplazada',
            'task_id': task.id
        }
    
    def _handle_project(self, item: InboxItem, data: Dict[str, Any]) -> Dict[str, Any]:
        from events.management.project_manager import ProjectManager
        from events.management.task_manager import TaskManager
        
        project_manager = ProjectManager(self.user)
        project = project_manager.create_project(
            title=item.title,
            description=item.description or f'Proyecto creado desde inbox: {item.title}',
            important=data.get('important', False)
        )
        
        task_manager = TaskManager(self.user)
        task = task_manager.create_task(
            title=f'Tarea inicial: {item.title}',
            description=item.description,
            important=data.get('important', False),
            project=project,
            assigned_to=self.user
        )
        
        item.is_processed = True
        item.processed_at = timezone.now()
        item.gtd_category = self.CATEGORY_ACCIONABLE
        item.action_type = self.ACTION_PROJECT
        
        content_type = ContentType.objects.get_for_model(project)
        item.processed_to_content_type = content_type
        item.processed_to_object_id = project.id
        item.save()
        
        self._log_action(item, 'project_created', {
            'project_id': project.id,
            'task_id': task.id
        })
        
        return {
            'success': True,
            'action': self.ACTION_PROJECT,
            'message': f'Proyecto "{item.title}" creado con tarea inicial',
            'project_id': project.id,
            'task_id': task.id
        }
    
    def _handle_default_task(self, item: InboxItem, data: Dict[str, Any]) -> Dict[str, Any]:
        from events.management.task_manager import TaskManager
        task_manager = TaskManager(self.user)
        
        task = task_manager.create_task(
            title=item.title,
            description=item.description,
            important=data.get('important', False),
            assigned_to=self.user,
            due_date=data.get('due_date')
        )
        
        item.is_processed = True
        item.processed_at = timezone.now()
        item.gtd_category = self.CATEGORY_ACCIONABLE
        item.action_type = self.ACTION_DO
        
        content_type = ContentType.objects.get_for_model(task)
        item.processed_to_content_type = content_type
        item.processed_to_object_id = task.id
        item.save()
        
        self._log_action(item, 'task_created', {'task_id': task.id})
        
        return {
            'success': True,
            'action': self.ACTION_DO,
            'message': f'Tarea "{item.title}" creada',
            'task_id': task.id
        }
    
    def _log_action(self, item: InboxItem, action: str, details: Dict[str, Any]):
        InboxItemHistory.objects.create(
            inbox_item=item,
            user=self.user,
            action=action,
            new_values=details
        )
    
    def get_clarification_stats(self) -> Dict[str, int]:
        total = InboxItem.objects.filter(created_by=self.user).count()
        processed = InboxItem.objects.filter(created_by=self.user, is_processed=True).count()
        unprocessed = total - processed
        
        accionable = InboxItem.objects.filter(created_by=self.user, gtd_category=self.CATEGORY_ACCIONABLE).count()
        no_accionable = InboxItem.objects.filter(created_by=self.user, gtd_category=self.CATEGORY_NO_ACCIONABLE).count()
        pendiente = InboxItem.objects.filter(created_by=self.user, gtd_category=self.CATEGORY_PENDIENTE).count()
        
        return {
            'total': total,
            'processed': processed,
            'unprocessed': unprocessed,
            'accionable': accionable,
            'no_accionable': no_accionable,
            'pendiente': pendiente,
            'processing_rate': round((processed / total * 100), 1) if total > 0 else 0
        }
