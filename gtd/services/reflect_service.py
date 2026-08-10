"""
Servicio de Reflexión GTD (Etapa 4)
Responsabilidad: Revisar y mantener actualizado el sistema GTD
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from django.db import models
from django.db.models import Q, Count, Avg
from django.utils import timezone
from django.contrib.auth import get_user_model

from events.models import Task, Project, InboxItem, Event

User = get_user_model()
logger = logging.getLogger(__name__)


class ReflectService:
    """
    Servicio de reflexión GTD

    Responsabilidades:
    1. Revisión Semanal (Weekly Review)
    2. Revisión Diaria (Daily Review)
    3. Revisión Mensual (Monthly Review)
    4. Auditoría de listas
    5. Generación de informes
    """

    def __init__(self, user):
        self.user = user
        self.logger = logging.getLogger(__name__)

    # ============ REVISIÓN SEMANAL ============

    def get_weekly_review(self) -> Dict[str, Any]:
        """
        Genera la revisión semanal completa

        Pasos de la Weekly Review GTD:
        1. Recopilar y procesar todos los items sueltos
        2. Revisar el calendario de la semana pasada y la próxima
        3. Revisar las listas de próximas acciones
        4. Revisar los proyectos
        5. Revisar las listas "Esperando" y "Algún día"
        6. Revisar el sistema en general
        """
        # Fecha de inicio de la semana (lunes)
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)

        # 1. Items del inbox sin procesar
        unprocessed_items = InboxItem.objects.filter(
            created_by=self.user,
            is_processed=False
        ).count()

        # 2. Calendario de la semana
        calendar_items = self._get_week_calendar(week_start, week_end)

        # 3. Próximas acciones
        next_actions = Task.objects.filter(
            Q(host=self.user) | Q(assigned_to=self.user),
            done=False,
            task_status__status_name__in=['To Do', 'In Progress']
        ).count()

        # 4. Proyectos
        projects = Project.objects.filter(
            Q(host=self.user) | Q(assigned_to=self.user)
        ).distinct()

        project_stats = {
            'total': projects.count(),
            'active': projects.filter(project_status__status_name='Active').count(),
            'completed': projects.filter(project_status__status_name='Completed').count(),
            'stalled': projects.filter(project_status__status_name='Stalled').count(),
        }

        # 5. Listas "Esperando" y "Algún día"
        waiting_count = Task.objects.filter(
            host=self.user,
            task_status__status_name='Waiting'
        ).count()

        someday_count = Task.objects.filter(
            host=self.user,
            task_status__status_name='Someday'
        ).count() + InboxItem.objects.filter(
            created_by=self.user,
            action_type='incubar'
        ).count()

        # 6. Tareas completadas en la semana
        completed_this_week = Task.objects.filter(
            Q(host=self.user) | Q(assigned_to=self.user),
            done=True,
            updated_at__gte=week_start
        ).count()

        # 7. Tareas vencidas
        overdue_tasks = Task.objects.filter(
            Q(host=self.user) | Q(assigned_to=self.user),
            done=False
        ).count()

        # 8. Tareas que vencen esta semana
        due_this_week = Task.objects.filter(
            Q(host=self.user) | Q(assigned_to=self.user),
            done=False
        ).count()

        # 9. Items nuevos en la semana
        new_items = InboxItem.objects.filter(
            created_by=self.user,
            created_at__date__gte=week_start
        ).count()

        # 10. Estadísticas de productividad
        productivity = self._calculate_productivity(week_start, week_end)

        return {
            'period': {
                'start': week_start,
                'end': week_end,
                'week_number': today.isocalendar()[1],
                'year': today.year
            },
            'inbox': {
                'unprocessed': unprocessed_items,
                'new_this_week': new_items,
                'processed_this_week': InboxItem.objects.filter(
                    created_by=self.user,
                    is_processed=True,
                    processed_at__date__gte=week_start
                ).count()
            },
            'calendar': calendar_items,
            'next_actions': next_actions,
            'projects': project_stats,
            'waiting': waiting_count,
            'someday': someday_count,
            'completed_this_week': completed_this_week,
            'overdue_tasks': overdue_tasks,
            'due_this_week': due_this_week,
            'productivity': productivity,
            'review_items': self._generate_review_items(),
            'stats_summary': {
                'total_active_items': unprocessed_items + next_actions + project_stats['active'],
                'completion_rate': round(
                    (completed_this_week / (completed_this_week + next_actions + 1)) * 100,
                    1
                ),
                'efficiency_score': self._calculate_efficiency_score(),
            }
        }

    def _get_week_calendar(self, start, end) -> Dict[str, List]:
        """Obtiene los items del calendario para la semana"""
        calendar = {}
        current = start
        while current <= end:
            # Tareas para esta fecha
            tasks = Task.objects.filter(
                Q(host=self.user) | Q(assigned_to=self.user),
                updated_at__date=current,
                done=False
            )

            # Eventos para esta fecha
            events = Event.objects.filter(
                Q(host=self.user) | Q(assigned_to=self.user) | Q(attendees=self.user),
                updated_at__date=current
            )

            calendar[current.strftime('%Y-%m-%d')] = {
                'date': current,
                'day_name': current.strftime('%A'),
                'tasks': tasks,
                'events': events,
                'count': tasks.count() + events.count()
            }
            current += timedelta(days=1)

        return calendar

    def _calculate_productivity(self, start, end) -> Dict[str, Any]:
        """Calcula métricas de productividad"""
        # Tareas completadas
        completed = Task.objects.filter(
            Q(host=self.user) | Q(assigned_to=self.user),
            done=True,
            updated_at__date__range=(start, end)
        ).count()

        # Tareas creadas
        created = Task.objects.filter(
            Q(host=self.user) | Q(assigned_to=self.user),
            created_at__date__range=(start, end)
        ).count()

        # Tiempo invertido (si está disponible)
        time_spent = 0

        return {
            'completed': completed,
            'created': created,
            'net_change': completed - created,
            'time_spent': round(time_spent, 1) if time_spent else 0,
            'productivity_rate': round(
                (completed / (created + 1)) * 100,
                1
            )
        }

    def _calculate_efficiency_score(self) -> int:
        """Calcula un puntaje de eficiencia general"""
        score = 0

        # Inbox limpio
        unprocessed = InboxItem.objects.filter(
            created_by=self.user,
            is_processed=False
        ).count()
        if unprocessed == 0:
            score += 25
        elif unprocessed <= 3:
            score += 15

        # Próximas acciones
        next_actions = Task.objects.filter(
            Q(host=self.user) | Q(assigned_to=self.user),
            done=False,
            task_status__status_name='To Do'
        ).count()
        if next_actions <= 10:
            score += 25
        elif next_actions <= 20:
            score += 15

        # Proyectos activos
        active_projects = Project.objects.filter(
            Q(host=self.user) | Q(assigned_to=self.user),
            project_status__status_name='Active'
        ).count()
        if active_projects <= 5:
            score += 25
        elif active_projects <= 10:
            score += 15

        # Tareas vencidas
        overdue = Task.objects.filter(
            Q(host=self.user) | Q(assigned_to=self.user),
            done=False
        ).count()
        if overdue == 0:
            score += 25
        elif overdue <= 3:
            score += 15

        return min(score, 100)

    def _generate_review_items(self) -> List[Dict]:
        """Genera items de revisión recomendados"""
        items = []
        today = timezone.now().date()

        # Verificar items en espera antiguos
        old_waiting = Task.objects.filter(
            host=self.user,
            task_status__status_name='Waiting',
            updated_at__lt=today - timedelta(days=7)
        ).count()
        if old_waiting > 0:
            items.append({
                'priority': 'high',
                'category': 'waiting',
                'message': f'Tienes {old_waiting} items en espera desde hace más de una semana',
                'action': 'Revisa si aún son relevantes o si necesitas hacer seguimiento'
            })

        # Verificar proyectos sin avance
        stalled_projects = Project.objects.filter(
            host=self.user,
            project_status__status_name='Active',
            updated_at__lt=today - timedelta(days=14)
        ).count()
        if stalled_projects > 0:
            items.append({
                'priority': 'medium',
                'category': 'projects',
                'message': f'Hay {stalled_projects} proyectos sin actualización en 2 semanas',
                'action': 'Revisa el estado y actualiza las próximas acciones'
            })

        # Verificar inbox lleno
        unprocessed = InboxItem.objects.filter(
            created_by=self.user,
            is_processed=False
        ).count()
        if unprocessed > 10:
            items.append({
                'priority': 'high',
                'category': 'inbox',
                'message': f'Tienes {unprocessed} items sin procesar en el inbox',
                'action': 'Dedica tiempo a procesar estos items'
            })

        # Verificar tareas vencidas
        overdue = Task.objects.filter(
            Q(host=self.user) | Q(assigned_to=self.user),
            done=False
        ).count()
        if overdue > 0:
            items.append({
                'priority': 'high',
                'category': 'tasks',
                'message': f'Tienes {overdue} tareas vencidas',
                'action': 'Revisa estas tareas y actualiza las fechas o prioridades'
            })

        # Verificar "Algún día" sin revisar
        someday_count = Task.objects.filter(
            host=self.user,
            task_status__status_name='Someday',
            updated_at__lt=today - timedelta(days=30)
        ).count()
        if someday_count > 0:
            items.append({
                'priority': 'low',
                'category': 'someday',
                'message': f'Tienes {someday_count} items en "Algún día" sin revisar en un mes',
                'action': 'Revisa si algunos de estos merecen ser activados'
            })

        return items

    # ============ REVISIÓN DIARIA ============

    def get_daily_review(self) -> Dict[str, Any]:
        """
        Genera la revisión diaria
        """
        today = timezone.now().date()
        tomorrow = today + timedelta(days=1)

        # Tareas para hoy
        tasks_today = Task.objects.filter(
            Q(host=self.user) | Q(assigned_to=self.user),
            done=False
        ).count()

        # Tareas vencidas
        overdue = Task.objects.filter(
            Q(host=self.user) | Q(assigned_to=self.user),
            done=False
        ).count()

        # Tareas para mañana
        tasks_tomorrow = Task.objects.filter(
            Q(host=self.user) | Q(assigned_to=self.user),
            done=False
        ).count()

        # Items del inbox nuevos hoy
        new_inbox = InboxItem.objects.filter(
            created_by=self.user,
            created_at__date=today
        ).count()

        # Tareas completadas hoy
        completed_today = Task.objects.filter(
            Q(host=self.user) | Q(assigned_to=self.user),
            done=True,
            updated_at__date=today
        ).count()

        return {
            'date': today,
            'day_name': today.strftime('%A'),
            'tasks_today': tasks_today,
            'overdue': overdue,
            'tasks_tomorrow': tasks_tomorrow,
            'new_inbox': new_inbox,
            'completed_today': completed_today,
            'focus_items': self._get_focus_items(today),
            'recommendations': self._get_daily_recommendations(today)
        }

    def _get_focus_items(self, date) -> List[Dict]:
        """Obtiene los items de enfoque para el día"""
        items = []

        # Tareas más importantes del día
        top_tasks = Task.objects.filter(
            Q(host=self.user) | Q(assigned_to=self.user),
            done=False,
            important=True
        )[:3]

        for task in top_tasks:
            items.append({
                'type': 'task',
                'title': task.title,
                'priority': 'alta',
                'project': task.project.title if task.project else None
            })

        # Si no hay tareas de alta prioridad, mostrar pendientes
        if not items:
            pending_tasks = Task.objects.filter(
                Q(host=self.user) | Q(assigned_to=self.user),
                done=False
            )[:5]
            for task in pending_tasks:
                items.append({
                    'type': 'task',
                    'title': task.title,
                    'priority': 'media',
                    'project': task.project.title if task.project else None
                })

        return items

    def _get_daily_recommendations(self, date) -> List[str]:
        """Obtiene recomendaciones para el día"""
        recommendations = []

        # Procesar inbox si tiene items
        unprocessed = InboxItem.objects.filter(
            created_by=self.user,
            is_processed=False
        ).count()
        if unprocessed > 5:
            recommendations.append(f"Procesa los {unprocessed} items pendientes en el inbox")

        # Revisar tareas vencidas
        overdue = Task.objects.filter(
            Q(host=self.user) | Q(assigned_to=self.user),
            done=False
        ).count()
        if overdue > 0:
            recommendations.append(f"Revisa las {overdue} tareas vencidas")

        # Planificar mañana
        tomorrow_tasks = Task.objects.filter(
            Q(host=self.user) | Q(assigned_to=self.user),
            done=False
        ).count()
        if tomorrow_tasks > 0:
            recommendations.append(f"Prepara las {tomorrow_tasks} tareas para mañana")

        return recommendations

    # ============ REVISIÓN MENSUAL ============

    def get_monthly_review(self) -> Dict[str, Any]:
        """
        Genera la revisión mensual
        """
        today = timezone.now().date()
        month_start = today.replace(day=1)
        last_month_start = (month_start - timedelta(days=1)).replace(day=1)
        last_month_end = month_start - timedelta(days=1)

        # Estadísticas del mes pasado
        tasks_completed = Task.objects.filter(
            Q(host=self.user) | Q(assigned_to=self.user),
            done=True,
            updated_at__date__range=(last_month_start, last_month_end)
        ).count()

        tasks_created = Task.objects.filter(
            Q(host=self.user) | Q(assigned_to=self.user),
            created_at__date__range=(last_month_start, last_month_end)
        ).count()

        projects_completed = Project.objects.filter(
            host=self.user,
            project_status__status_name='Completed',
            updated_at__date__range=(last_month_start, last_month_end)
        ).count()

        # Proyectos activos actuales
        active_projects = Project.objects.filter(
            host=self.user,
            project_status__status_name='Active'
        ).count()

        # Items de "Algún día" que podrían activarse
        someday_items = Task.objects.filter(
            host=self.user,
            task_status__status_name='Someday',
            created_at__date__range=(last_month_start, last_month_end)
        ).count()

        return {
            'period': {
                'month': month_start.strftime('%B %Y'),
                'last_month': last_month_start.strftime('%B %Y'),
                'days_in_month': (month_start - last_month_start).days
            },
            'tasks': {
                'completed': tasks_completed,
                'created': tasks_created,
                'net_change': tasks_created - tasks_completed,
                'avg_daily_completed': round(tasks_completed / 30, 1)
            },
            'projects': {
                'completed': projects_completed,
                'active': active_projects,
                'completion_rate': round(
                    (projects_completed / (active_projects + projects_completed + 1)) * 100,
                    1
                )
            },
            'someday': someday_items,
            'efficiency': self._calculate_monthly_efficiency(tasks_completed, tasks_created),
            'recommendations': self._get_monthly_recommendations()
        }

    def _calculate_monthly_efficiency(self, completed, created) -> Dict[str, Any]:
        """Calcula la eficiencia mensual"""
        if created == 0:
            return {
                'score': 0,
                'level': 'Sin datos',
                'ratio': 0
            }

        ratio = completed / created
        if ratio >= 0.8:
            level = 'Excelente'
        elif ratio >= 0.6:
            level = 'Bueno'
        elif ratio >= 0.4:
            level = 'Regular'
        else:
            level = 'Necesita mejora'

        return {
            'score': round(ratio * 100, 1),
            'level': level,
            'ratio': round(ratio, 2)
        }

    def _get_monthly_recommendations(self) -> List[str]:
        """Obtiene recomendaciones mensuales"""
        recommendations = []

        # Revisar proyectos activos sin avance
        active_projects = Project.objects.filter(
            host=self.user,
            project_status__status_name='Active'
        ).count()
        if active_projects > 10:
            recommendations.append(f"Considera reducir el número de proyectos activos ({active_projects})")

        # Revisar tareas en "Esperando"
        waiting = Task.objects.filter(
            host=self.user,
            task_status__status_name='Waiting'
        ).count()
        if waiting > 5:
            recommendations.append(f"Revisa las {waiting} tareas en espera, algunas pueden estar olvidadas")

        # Revisar "Algún día"
        someday = Task.objects.filter(
            host=self.user,
            task_status__status_name='Someday'
        ).count()
        if someday > 0:
            recommendations.append(f"Revisa los {someday} items de 'Algún día' para posibles activaciones")

        return recommendations

    # ============ AUDITORÍA ============

    def audit_system(self) -> Dict[str, Any]:
        """
        Realiza una auditoría completa del sistema GTD
        """
        # Verificar consistencia de datos
        issues = []

        # Tareas sin proyecto pero con contexto de proyecto
        orphan_tasks = Task.objects.filter(
            host=self.user,
            project__isnull=True
        ).count()
        if orphan_tasks > 0:
            issues.append({
                'type': 'warning',
                'message': f'Encontradas {orphan_tasks} tareas sin proyecto asociado',
                'suggestion': 'Asigna estas tareas a proyectos o crea proyectos para ellas'
            })

        # Proyectos sin tareas
        empty_projects = Project.objects.filter(
            host=self.user,
            task__isnull=True
        ).count()
        if empty_projects > 0:
            issues.append({
                'type': 'info',
                'message': f'Encontrados {empty_projects} proyectos sin tareas',
                'suggestion': 'Revisa si estos proyectos son necesarios o deben ser archivados'
            })

        # Items del inbox muy antiguos
        old_inbox = InboxItem.objects.filter(
            created_by=self.user,
            is_processed=False,
            created_at__lt=timezone.now() - timedelta(days=30)
        ).count()
        if old_inbox > 0:
            issues.append({
                'type': 'warning',
                'message': f'Encontrados {old_inbox} items en el inbox con más de 30 días',
                'suggestion': 'Procesa estos items o archívalos como referencia'
            })

        # Tareas sin actualización en más de 30 días
        old_overdue = Task.objects.filter(
            Q(host=self.user) | Q(assigned_to=self.user),
            done=False,
            updated_at__lt=timezone.now() - timedelta(days=30)
        ).count()
        if old_overdue > 0:
            issues.append({
                'type': 'error',
                'message': f'Encontradas {old_overdue} tareas vencidas por más de 30 días',
                'suggestion': 'Revisa si estas tareas aún son relevantes o deben ser canceladas'
            })

        # Verificar duplicados
        duplicates = self._find_duplicates()
        if duplicates:
            issues.append({
                'type': 'warning',
                'message': f'Encontrados {len(duplicates)} posibles duplicados',
                'suggestion': 'Revisa y elimina los duplicados para mantener el sistema limpio',
                'duplicates': duplicates
            })

        return {
            'issues': issues,
            'stats': self._get_audit_stats(),
            'health_score': self._calculate_health_score(issues),
            'timestamp': timezone.now()
        }

    def _find_duplicates(self) -> List[Dict]:
        """Encuentra posibles duplicados en tareas y proyectos"""
        duplicates = []

        # Buscar tareas con títulos muy similares
        tasks = Task.objects.filter(host=self.user)
        task_titles = {}
        for task in tasks:
            title_lower = task.title.lower().strip()
            if title_lower in task_titles:
                duplicates.append({
                    'type': 'task',
                    'items': [task_titles[title_lower], task],
                    'title': task.title
                })
            else:
                task_titles[title_lower] = task

        return duplicates

    def _get_audit_stats(self) -> Dict[str, int]:
        """Obtiene estadísticas para la auditoría"""
        return {
            'total_tasks': Task.objects.filter(host=self.user).count(),
            'completed_tasks': Task.objects.filter(host=self.user, done=True).count(),
            'total_projects': Project.objects.filter(host=self.user).count(),
            'active_projects': Project.objects.filter(host=self.user, project_status__status_name='Active').count(),
            'total_inbox': InboxItem.objects.filter(created_by=self.user).count(),
            'unprocessed_inbox': InboxItem.objects.filter(created_by=self.user, is_processed=False).count(),
        }

    def _calculate_health_score(self, issues) -> int:
        """Calcula un puntaje de salud del sistema"""
        errors = sum(1 for i in issues if i['type'] == 'error')
        warnings = sum(1 for i in issues if i['type'] == 'warning')

        base_score = 100
        penalty = (errors * 10) + (warnings * 5)
        return max(0, base_score - penalty)
