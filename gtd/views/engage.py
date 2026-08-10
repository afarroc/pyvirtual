"""
ETAPA 5: EJECUTAR (Engage)
Propósito: Ayudar al usuario a elegir qué hacer en cada momento
"""

import logging
from datetime import datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from events.models import Task, Project

from ..services.engage_service import EngageService
from .base import GTDViewMixin

logger = logging.getLogger(__name__)


@login_required
def engage_dashboard(request):
    """
    Vista principal de ejecución GTD
    """
    service = EngageService(request.user)
    dashboard_data = service.get_execution_dashboard()

    context = {
        'title': 'Ejecutar GTD',
        'subtitle': 'Elige qué hacer ahora',
        'dashboard': dashboard_data,
    }

    return render(request, 'gtd/engage/dashboard.html', context)


@login_required
def engage_today(request):
    """
    Vista de tareas para hoy
    """
    service = EngageService(request.user)
    today_tasks = service._get_today_tasks()

    context = {
        'title': 'Hoy',
        'subtitle': timezone.now().date().strftime('%A %d/%m/%Y'),
        'today_tasks': today_tasks,
    }

    return render(request, 'gtd/engage/today.html', context)


@login_required
def engage_context(request, context):
    """
    Vista de tareas por contexto
    """
    service = EngageService(request.user)
    tasks = service.get_tasks_by_context(context)

    context_data = {
        'title': f'Contexto: {context}',
        'subtitle': f'Tareas disponibles en {context}',
        'context': context,
        'tasks': tasks,
    }

    return render(request, 'gtd/engage/context.html', context_data)


@login_required
def engage_by_time(request, minutes):
    """
    Vista de tareas por tiempo disponible
    """
    service = EngageService(request.user)
    tasks = service.get_tasks_by_time(minutes)

    context = {
        'title': f'Tareas de {minutes} minutos',
        'subtitle': f'Tareas que puedes completar en {minutes} minutos o menos',
        'minutes': minutes,
        'tasks': tasks,
    }

    return render(request, 'gtd/engage/by_time.html', context)


@login_required
def engage_by_energy(request, level):
    """
    Vista de tareas por nivel de energía
    """
    service = EngageService(request.user)
    dashboard_data = service.get_execution_dashboard()

    # Mapear nivel de energía a clave del diccionario
    energy_map = {
        'alta': 'high_energy',
        'media': 'medium_energy',
        'baja': 'low_energy',
    }

    energy_key = energy_map.get(level, 'medium_energy')
    tasks = dashboard_data['energy_tasks'].get(energy_key, [])

    context = {
        'title': f'Energía: {level.capitalize()}',
        'subtitle': f'Tareas para cuando tienes energía {level}',
        'level': level,
        'energy_key': energy_key,
        'tasks': tasks,
    }

    return render(request, 'gtd/engage/by_energy.html', context)


# ============ API ENDPOINTS ============

@login_required
@require_http_methods(["GET"])
def engage_stats_api(request):
    """
    API endpoint para estadísticas de ejecución
    """
    service = EngageService(request.user)
    stats = service._get_execution_stats()

    return JsonResponse({
        'success': True,
        'stats': stats,
        'timestamp': timezone.now().isoformat()
    })
