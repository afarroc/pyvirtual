"""
Servicio de Ejecución GTD (Etapa 5)
Responsabilidad: Ayudar al usuario a elegir qué hacer en cada momento
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from django.db import models
from django.db.models import Q, Count
from django.utils import timezone
from django.contrib.auth import get_user_model

from events.models import Task, Project

User = get_user_model()
logger = logging.getLogger(__name__)


class EngageService:
    """
    Servicio de ejecución GTD

    Ayuda a decidir qué hacer basado en:
    1. Contexto (dónde estás, qué tienes disponible)
    2. Tiempo disponible
    3. Energía disponible
    4. Prioridad
    """

    def __init__(self, user):
        self.user = user
        self.logger = logging.getLogger(__name__)

    # ============ DASHBOARD DE EJECUCIÓN ============

    def get_execution_dashboard(self) -> Dict[str, Any]:
        """
        Obtiene el dashboard de ejecución con recomendaciones
        """
        # Contextos disponibles
        contexts = self._get_available_contexts()

        # Tareas por contexto
        tasks_by_context = {}
        for context in contexts:
            tasks_by_context[context] = self._get_tasks_for_context(context, limit=5)

        # Tareas de hoy
        today_tasks = self._get_today_tasks()

        # Próximas tareas importantes
        important_tasks = self._get_important_tasks()

        # Tareas por energía requerida
        energy_tasks = self._get_tasks_by_energy()

        # Tareas rápidas (menos de 15 minutos)
        quick_tasks = self._get_quick_tasks()

        return {
            'contexts': contexts,
            'tasks_by_context': tasks_by_context,
            'today_tasks': today_tasks,
            'important_tasks': important_tasks,
            'energy_tasks': energy_tasks,
            'quick_tasks': quick_tasks,
            'stats': self._get_execution_stats(),
            'recommendations': self._get_recommendations(),
        }

    def _get_available_contexts(self) -> List[str]:
        """Obtiene contextos disponibles basados en tareas actuales"""
        contexts = set(['@sin_contexto'])

        tasks = Task.objects.filter(
            Q(host=self.user) | Q(assigned_to=self.user),
            done=False,
            task_status__status_name__in=['To Do', 'In Progress']
        )

        for task in tasks:
            text = f"{task.title} {task.description or ''}"
            context_matches = re.findall(r'@([a-zA-Z0-9_]+)', text)
            contexts.update([f"@{ctx}" for ctx in context_matches])

        return sorted(list(contexts))

    def _get_tasks_for_context(self, context: str, limit: int = 5) -> List[Dict]:
        """Obtiene tareas para un contexto específico"""
        tasks = Task.objects.filter(
            Q(host=self.user) | Q(assigned_to=self.user),
            done=False,
            task_status__status_name__in=['To Do', 'In Progress']
        )

        # Filtrar por contexto
        filtered = []
        for task in tasks:
            text = f"{task.title} {task.description or ''}"
            if context == '@sin_contexto':
                if not re.search(r'@[a-zA-Z0-9_]+', text):
                    filtered.append(task)
            elif context in text:
                filtered.append(task)

        # Ordenar por prioridad y fecha
        filtered.sort(key=lambda x: (
            {'alta': 0, 'media': 1, 'baja': 2}.get('alta' if getattr(x, 'important', False) else 'media', 1),
            getattr(x, 'due_date', None) or datetime.max
        ))

        return [{
            'task': task,
            'priority': 'alta' if getattr(task, 'important', False) else 'media',
            'project': task.project.title if task.project else None,
            'due_date': getattr(task, 'due_date', None),
            'estimated_time': getattr(task, 'estimated_time', None)
        } for task in filtered[:limit]]

    def _get_today_tasks(self) -> List[Dict]:
        """Obtiene tareas programadas para hoy"""
        today = timezone.now().date()

        tasks = Task.objects.filter(
            Q(host=self.user) | Q(assigned_to=self.user),
            done=False
        ).order_by('important', '-created_at')

        return [{
            'task': task,
            'priority': 'alta' if getattr(task, 'important', False) else 'media',
            'project': task.project.title if task.project else None,
            'is_overdue': getattr(task, 'due_date', None) and getattr(task, 'due_date', None) < today
        } for task in tasks]

    def _get_important_tasks(self, limit: int = 10) -> List[Dict]:
        """Obtiene tareas importantes"""
        tasks = Task.objects.filter(
            Q(host=self.user) | Q(assigned_to=self.user),
            done=False,
            important=True
        ).order_by('-created_at')[:limit]

        return [{
            'task': task,
            'project': task.project.title if task.project else None,
            'due_date': getattr(task, 'due_date', None),
            'is_overdue': getattr(task, 'due_date', None) and getattr(task, 'due_date', None) < timezone.now().date()
        } for task in tasks]

    def _get_tasks_by_energy(self) -> Dict[str, List[Dict]]:
        """
        Clasifica tareas por nivel de energía requerido
        Basado en complejidad, creatividad y esfuerzo
        """
        tasks = Task.objects.filter(
            Q(host=self.user) | Q(assigned_to=self.user),
            done=False,
            task_status__status_name__in=['To Do', 'In Progress']
        )

        result = {
            'high_energy': [],
            'medium_energy': [],
            'low_energy': []
        }

        for task in tasks:
            # Determinar energía basado en palabras clave
            text = f"{task.title} {task.description or ''}".lower()

            energy = 'medium_energy'

            # Palabras que indican alta energía
            high_indicators = ['complejo', 'difícil', 'crear', 'diseñar', 'planificar',
                             'estrategia', 'análisis', 'investigar']
            if any(ind in text for ind in high_indicators):
                energy = 'high_energy'

            # Palabras que indican baja energía
            low_indicators = ['revisar', 'organizar', 'ordenar', 'limpiar',
                            'archivar', 'responder', 'leer']
            if any(ind in text for ind in low_indicators):
                energy = 'low_energy'

            result[energy].append({
                'task': task,
                'project': task.project.title if task.project else None,
                'priority': 'alta' if getattr(task, 'important', False) else 'media',
                'estimated_time': getattr(task, 'estimated_time', None)
            })

        # Limitar cantidad
        for key in result:
            result[key] = result[key][:5]

        return result

    def _get_quick_tasks(self, limit: int = 5) -> List[Dict]:
        """Obtiene tareas rápidas (menos de 15 minutos)"""
        tasks = Task.objects.filter(
            Q(host=self.user) | Q(assigned_to=self.user),
            done=False,
            task_status__status_name__in=['To Do', 'In Progress']
        )

        quick = []
        for task in tasks:
            estimated_time = getattr(task, 'estimated_time', None)
            if estimated_time and estimated_time <= 15:
                quick.append({
                    'task': task,
                    'estimated_time': estimated_time,
                    'project': task.project.title if task.project else None,
                    'priority': 'alta' if getattr(task, 'important', False) else 'media'
                })

        quick.sort(key=lambda x: x['estimated_time'])
        return quick[:limit]

    def _get_execution_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas de ejecución"""
        total_tasks = Task.objects.filter(
            Q(host=self.user) | Q(assigned_to=self.user),
            done=False
        ).count()

        high_priority = Task.objects.filter(
            Q(host=self.user) | Q(assigned_to=self.user),
            done=False,
            important=True
        ).count()

        overdue = Task.objects.filter(
            Q(host=self.user) | Q(assigned_to=self.user),
            done=False
        ).count()

        due_today = Task.objects.filter(
            Q(host=self.user) | Q(assigned_to=self.user),
            done=False
        ).count()

        return {
            'total': total_tasks,
            'high_priority': high_priority,
            'overdue': overdue,
            'due_today': due_today,
            'completion_rate': self._calculate_completion_rate(),
        }

    def _calculate_completion_rate(self) -> float:
        """Calcula la tasa de completación de tareas"""
        total = Task.objects.filter(
            Q(host=self.user) | Q(assigned_to=self.user)
        ).count()

        if total == 0:
            return 0.0

        completed = Task.objects.filter(
            Q(host=self.user) | Q(assigned_to=self.user),
            done=True
        ).count()

        return round((completed / total) * 100, 1)

    def _get_recommendations(self) -> List[Dict]:
        """Obtiene recomendaciones para la ejecución"""
        recommendations = []
        today = timezone.now().date()

        # Recomendación basada en tareas antiguas pendientes
        week_ago = timezone.now() - timedelta(days=7)
        overdue = Task.objects.filter(
            Q(host=self.user) | Q(assigned_to=self.user),
            done=False,
            created_at__lt=week_ago
        ).count()
        if overdue > 0:
            recommendations.append({
                'priority': 'high',
                'message': f'Tienes {overdue} tareas pendientes desde hace más de una semana',
                'action': 'Enfócate en estas tareas primero'
            })

        # Recomendación basada en tareas de hoy
        today = timezone.now().date()
        today_start = timezone.make_aware(datetime.combine(today, datetime.min.time()))
        today_end = timezone.make_aware(datetime.combine(today, datetime.max.time()))
        due_today = Task.objects.filter(
            Q(host=self.user) | Q(assigned_to=self.user),
            done=False,
            created_at__range=(today_start, today_end)
        ).count()
        if due_today > 0:
            recommendations.append({
                'priority': 'medium',
                'message': f'Tienes {due_today} tareas creadas hoy',
                'action': 'Completa estas tareas antes del final del día'
            })

        # Recomendación basada en tareas importantes
        important = Task.objects.filter(
            Q(host=self.user) | Q(assigned_to=self.user),
            done=False,
            important=True
        ).count()
        if important > 0:
            recommendations.append({
                'priority': 'high',
                'message': f'Tienes {important} tareas de alta prioridad',
                'action': 'Empieza tu día con estas tareas'
            })

        return recommendations

    # ============ FILTRADO POR CONTEXTO ============

    def get_tasks_by_context(self, context: str) -> List[Dict]:
        """Obtiene todas las tareas para un contexto específico"""
        return self._get_tasks_for_context(context, limit=100)

    # ============ FILTRADO POR TIEMPO ============

    def get_tasks_by_time(self, minutes: int) -> List[Dict]:
        """Obtiene tareas que se pueden completar en un tiempo determinado"""
        tasks = Task.objects.filter(
            Q(host=self.user) | Q(assigned_to=self.user),
            done=False,
            task_status__status_name__in=['To Do', 'In Progress']
        )

        filtered = []
        for task in tasks:
            estimated_time = getattr(task, 'estimated_time', None)
            if estimated_time and estimated_time <= minutes:
                filtered.append({
                    'task': task,
                    'estimated_time': estimated_time,
                    'project': task.project.title if task.project else None,
                    'priority': 'alta' if getattr(task, 'important', False) else 'media'
                })

        filtered.sort(key=lambda x: x['estimated_time'])
        return filtered
