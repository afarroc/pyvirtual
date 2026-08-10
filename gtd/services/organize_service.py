"""
Servicio de Organización GTD (Etapa 3)
Responsabilidad: Organizar los items procesados en listas accionables según GTD
"""

import logging
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime, timedelta
from django.db import models
from django.db.models import Q, Count, Avg, Sum
from django.contrib.auth import get_user_model
from django.utils import timezone

from events.models import Task, Project, Event, InboxItem, TaskStatus, ProjectStatus

User = get_user_model()
logger = logging.getLogger(__name__)


class OrganizeService:
    """
    Servicio de organización GTD
    
    Listas GTD:
    1. Próximas Acciones (Next Actions) - Tareas concretas por contexto
    2. Proyectos - Resultados que requieren múltiples pasos
    3. Esperando (Waiting For) - Tareas delegadas
    4. Algún día / Quizás (Someday/Maybe) - Ideas para el futuro
    5. Referencias - Información de archivo
    6. Agenda - Calendario y fechas específicas
    """
    
    def __init__(self, user):
        self.user = user
        self.logger = logging.getLogger(__name__)
    
    def get_next_actions(self, context: Optional[str] = None, limit: int = 50) -> Dict[str, Any]:
        todo_status = TaskStatus.objects.filter(status_name__in=['To Do', 'In Progress']).first()
        
        tasks = Task.objects.filter(
            Q(host=self.user) | Q(assigned_to=self.user),
            done=False
        )
        
        if todo_status:
            tasks = tasks.filter(task_status=todo_status)
        
        tasks = tasks.exclude(
            dependencies__depends_on__done=False
        ).distinct()
        
        contexts = {}
        for task in tasks.select_related('project', 'task_status', 'assigned_to'):
            task_contexts = self._extract_contexts(task)
            
            if not task_contexts:
                task_contexts = ['@sin_contexto']
            
            for ctx in task_contexts:
                if context and context != ctx:
                    continue
                if ctx not in contexts:
                    contexts[ctx] = []
                contexts[ctx].append({
                    'task': task,
                    'priority': 'alta' if getattr(task, 'important', False) else 'media',
                    'project': task.project.title if task.project else None,
                    'due_date': getattr(task, 'due_date', None),
                    'estimated_time': getattr(task, 'estimated_time', None)
                })
        
        for ctx in contexts:
            contexts[ctx].sort(key=lambda x: (
                {'alta': 0, 'media': 1, 'baja': 2}.get(x['priority'], 1),
                x['due_date'] or datetime.max
            ))
            contexts[ctx] = contexts[ctx][:limit]
        
        stats = {
            'total': sum(len(items) for items in contexts.values()),
            'contexts': len(contexts),
            'by_priority': {
                'alta': sum(1 for items in contexts.values() for item in items if item['priority'] == 'alta'),
                'media': sum(1 for items in contexts.values() for item in items if item['priority'] == 'media'),
                'baja': sum(1 for items in contexts.values() for item in items if item['priority'] == 'baja'),
            },
            'overdue': sum(
                1 for items in contexts.values() 
                for item in items 
                if item.get('due_date') and item['due_date'] < timezone.now().date()
            ),
            'due_today': sum(
                1 for items in contexts.values() 
                for item in items 
                if item.get('due_date') and item['due_date'] == timezone.now().date()
            ),
        }
        
        return {
            'contexts': contexts,
            'stats': stats,
            'available_contexts': list(contexts.keys())
        }
    
    def _extract_contexts(self, task) -> List[str]:
        contexts = []
        
        text = f"{task.title} {task.description or ''}"
        import re
        context_matches = re.findall(r'@([a-zA-Z0-9_]+)', text)
        contexts.extend([f"@{ctx}" for ctx in context_matches])
        
        if hasattr(task, 'tags'):
            for tag in task.tags.all():
                if tag.name.startswith('@'):
                    contexts.append(tag.name)
        
        if not contexts and hasattr(task, 'project') and task.project:
            project_contexts = self._extract_contexts(task.project)
            contexts.extend(project_contexts)
        
        return list(set(contexts))
    
    def get_projects(self, status: Optional[str] = None, limit: int = 50) -> Dict[str, Any]:
        projects = Project.objects.filter(
            Q(host=self.user) | Q(assigned_to=self.user) | Q(attendees=self.user)
        ).distinct()
        
        if status:
            projects = projects.filter(project_status__status_name=status)
        
        projects = projects.select_related('project_status', 'event')
        
        organized = {}
        for project in projects:
            status_name = project.project_status.status_name if project.project_status else 'Sin estado'
            if status_name not in organized:
                organized[status_name] = []
            
            total_tasks = project.task_set.count()
            completed_tasks = project.task_set.filter(done=True).count()
            progress = round((completed_tasks / total_tasks * 100) if total_tasks > 0 else 0)
            
            organized[status_name].append({
                'project': project,
                'progress': progress,
                'total_tasks': total_tasks,
                'completed_tasks': completed_tasks,
                'next_action': self._get_next_action_for_project(project),
            })
        
        stats = {
            'total': sum(len(items) for items in organized.values()),
            'by_status': {status: len(items) for status, items in organized.items()},
            'active': len(organized.get('Active', [])) + len(organized.get('In Progress', [])),
            'completed': len(organized.get('Completed', [])),
            'blocked': len(organized.get('Blocked', [])),
        }
        
        return {
            'projects': organized,
            'stats': stats,
            'available_statuses': list(organized.keys())
        }
    
    def _get_next_action_for_project(self, project) -> Optional[Dict]:
        next_task = project.task_set.filter(
            done=False
        ).order_by('-important', 'created_at').first()
        
        if next_task:
            return {
                'task': next_task,
                'title': next_task.title,
                'priority': 'alta' if getattr(next_task, 'important', False) else 'media',
                'due_date': getattr(next_task, 'due_date', None)
            }
        return None
    
    def get_project_detail(self, project_id: int) -> Dict[str, Any]:
        try:
            project = Project.objects.get(
                id=project_id,
                host=self.user
            )
        except Project.DoesNotExist:
            return {'success': False, 'error': 'Proyecto no encontrado'}
        
        tasks = project.task_set.all().select_related('task_status', 'assigned_to')
        
        tasks_by_status = {}
        for task in tasks:
            status = task.task_status.status_name if task.task_status else 'Sin estado'
            if status not in tasks_by_status:
                tasks_by_status[status] = []
            tasks_by_status[status].append(task)
        
        members = list(project.attendees.all()) + [project.assigned_to] if project.assigned_to else []
        members = list(set(members))
        
        return {
            'success': True,
            'project': project,
            'tasks_by_status': tasks_by_status,
            'members': members,
            'total_tasks': tasks.count(),
            'completed_tasks': tasks.filter(done=True).count(),
            'next_action': self._get_next_action_for_project(project),
            'timeline': self._get_project_timeline(project),
        }
    
    def _get_project_timeline(self, project) -> Dict[str, Any]:
        completed = project.task_set.filter(
            done=True
        ).order_by('updated_at')
        
        in_progress = project.task_set.filter(
            done=False,
            task_status__status_name='In Progress'
        )
        
        pending = project.task_set.filter(
            done=False,
            task_status__status_name='To Do'
        )
        
        return {
            'completed_count': completed.count(),
            'in_progress_count': in_progress.count(),
            'pending_count': pending.count(),
            'completion_rate': round((completed.count() / project.task_set.count() * 100) if project.task_set.count() > 0 else 0, 1)
        }
    
    def get_waiting_for(self) -> Dict[str, Any]:
        delegated_tasks = Task.objects.filter(
            host=self.user,
            done=False,
            assigned_to__isnull=False
        ).exclude(assigned_to=self.user)
        
        waiting_tasks = Task.objects.filter(
            assigned_to=self.user,
            done=False,
            task_status__status_name='Waiting'
        )
        
        waiting_inbox = InboxItem.objects.filter(
            created_by=self.user,
            is_processed=False,
            gtd_category='pendiente'
        )
        
        result = {
            'delegated': [],
            'waiting_for_response': [],
            'waiting_inbox': [],
            'stats': {
                'total': 0,
                'delegated_count': 0,
                'waiting_count': 0,
                'inbox_waiting_count': 0,
            }
        }
        
        for task in delegated_tasks.select_related('assigned_to', 'project'):
            result['delegated'].append({
                'task': task,
                'delegated_to': task.assigned_to,
                'delegated_at': task.updated_at,
                'project': task.project,
                'waiting_time': (timezone.now() - task.updated_at).days,
                'is_overdue': False,
            })
        
        for task in waiting_tasks.select_related('host', 'project'):
            result['waiting_for_response'].append({
                'task': task,
                'waiting_from': task.host,
                'waiting_at': task.updated_at,
                'project': task.project,
                'waiting_time': (timezone.now() - task.updated_at).days,
                'is_overdue': False,
            })
        
        for item in waiting_inbox:
            result['waiting_inbox'].append({
                'item': item,
                'created_at': item.created_at,
                'waiting_time': (timezone.now() - item.created_at).days,
            })
        
        result['stats']['delegated_count'] = len(result['delegated'])
        result['stats']['waiting_count'] = len(result['waiting_for_response'])
        result['stats']['inbox_waiting_count'] = len(result['waiting_inbox'])
        result['stats']['total'] = (
            result['stats']['delegated_count'] +
            result['stats']['waiting_count'] +
            result['stats']['inbox_waiting_count']
        )
        
        return result
    
    def get_someday_maybe(self) -> Dict[str, Any]:
        inbox_items = InboxItem.objects.filter(
            created_by=self.user,
            action_type='incubar',
            is_processed=True
        ).order_by('-created_at')
        
        someday_projects = Project.objects.filter(
            host=self.user,
            project_status__status_name='Someday'
        ).order_by('-updated_at')
        
        someday_tasks = Task.objects.filter(
            host=self.user,
            task_status__status_name='Someday'
        ).order_by('-updated_at')
        
        return {
            'inbox_items': inbox_items,
            'projects': someday_projects,
            'tasks': someday_tasks,
            'stats': {
                'total': inbox_items.count() + someday_projects.count() + someday_tasks.count(),
                'inbox_count': inbox_items.count(),
                'projects_count': someday_projects.count(),
                'tasks_count': someday_tasks.count(),
            }
        }
    
    def get_references(self, search: Optional[str] = None, limit: int = 50) -> Dict[str, Any]:
        inbox_items = InboxItem.objects.filter(
            created_by=self.user,
            action_type='archivar',
            is_processed=True
        )
        
        archived_tasks = Task.objects.filter(
            host=self.user,
            task_status__status_name='Archived'
        )
        
        archived_projects = Project.objects.filter(
            host=self.user,
            project_status__status_name='Archived'
        )
        
        if search:
            inbox_items = inbox_items.filter(
                Q(title__icontains=search) | Q(description__icontains=search)
            )
            archived_tasks = archived_tasks.filter(
                Q(title__icontains=search) | Q(description__icontains=search)
            )
            archived_projects = archived_projects.filter(
                Q(title__icontains=search) | Q(description__icontains=search)
            )
        
        return {
            'inbox_items': inbox_items[:limit],
            'tasks': archived_tasks[:limit],
            'projects': archived_projects[:limit],
            'stats': {
                'total': inbox_items.count() + archived_tasks.count() + archived_projects.count(),
                'inbox_count': inbox_items.count(),
                'tasks_count': archived_tasks.count(),
                'projects_count': archived_projects.count(),
            }
        }
    
    def get_calendar_items(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> Dict[str, Any]:
        if not start_date:
            start_date = timezone.now().date()
        if not end_date:
            end_date = start_date + timedelta(days=30)
        
        start_datetime = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
        end_datetime = timezone.make_aware(datetime.combine(end_date, datetime.max.time()))
        
        tasks = Task.objects.filter(
            Q(host=self.user) | Q(assigned_to=self.user),
            created_at__range=(start_datetime, end_datetime)
        ).select_related('project', 'assigned_to')
        
        projects = Project.objects.filter(
            host=self.user,
            due_date__range=(start_date, end_date)
        )
        
        events = Event.objects.filter(
            Q(host=self.user) | Q(assigned_to=self.user) | Q(attendees=self.user),
            updated_at__range=(start_datetime, end_datetime)
        ).select_related('event_status')
        
        calendar = {}
        current = start_date
        while current <= end_date:
            date_str = current.strftime('%Y-%m-%d')
            calendar[date_str] = {
                'date': current,
                'tasks': [],
                'projects': [],
                'events': [],
                'count': 0
            }
            current += timedelta(days=1)
        
        for task in tasks:
            date_str = task.created_at.strftime('%Y-%m-%d') if task.created_at else None
            if date_str and date_str in calendar:
                calendar[date_str]['tasks'].append(task)
                calendar[date_str]['count'] += 1
        
        for project in projects:
            date_str = getattr(project, 'due_date', None)
            if getattr(project, 'due_date', None):
                date_str = getattr(project, 'due_date').strftime('%Y-%m-%d')
            if date_str and date_str in calendar:
                calendar[date_str]['projects'].append(project)
                calendar[date_str]['count'] += 1
        
        for event in events:
            date_str = event.updated_at.strftime('%Y-%m-%d')
            if date_str in calendar:
                calendar[date_str]['events'].append(event)
                calendar[date_str]['count'] += 1
        
        return {
            'calendar': calendar,
            'start_date': start_date,
            'end_date': end_date,
            'stats': {
                'total': sum(day['count'] for day in calendar.values()),
                'days_with_items': sum(1 for day in calendar.values() if day['count'] > 0),
                'upcoming': sum(1 for date_str, day in calendar.items() if day['count'] > 0 and datetime.strptime(date_str, '%Y-%m-%d').date() >= timezone.now().date()),
            }
        }
    
    def get_organize_stats(self) -> Dict[str, Any]:
        next_actions = self.get_next_actions()
        projects = self.get_projects()
        waiting = self.get_waiting_for()
        someday = self.get_someday_maybe()
        references = self.get_references()
        
        return {
            'next_actions': next_actions['stats'],
            'projects': projects['stats'],
            'waiting': waiting['stats'],
            'someday': someday['stats'],
            'references': references['stats'],
            'total_active': (
                next_actions['stats']['total'] +
                projects['stats']['active'] +
                waiting['stats']['total']
            )
        }
