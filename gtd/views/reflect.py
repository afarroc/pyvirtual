"""
ETAPA 4: REFLEXIONAR (Reflect)
Propósito: Revisar y mantener actualizado el sistema GTD
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

from ..services.reflect_service import ReflectService
from .base import GTDViewMixin

logger = logging.getLogger(__name__)


@login_required
def reflect_dashboard(request):
    """
    Vista principal de reflexión GTD
    """
    service = ReflectService(request.user)

    # Obtener todas las revisiones
    weekly = service.get_weekly_review()
    daily = service.get_daily_review()
    audit = service.audit_system()

    context = {
        'title': 'Reflexionar GTD',
        'subtitle': 'Revisa y mantén actualizado tu sistema',
        'weekly': weekly,
        'daily': daily,
        'audit': audit,
        'health_score': audit['health_score'],
    }

    return render(request, 'gtd/reflect/dashboard.html', context)


@login_required
def reflect_weekly(request):
    """
    Vista de revisión semanal detallada
    """
    service = ReflectService(request.user)
    weekly = service.get_weekly_review()

    context = {
        'title': 'Revisión Semanal',
        'subtitle': 'Semana del ' + weekly['period']['start'].strftime('%d/%m/%Y'),
        'weekly': weekly,
    }

    return render(request, 'gtd/reflect/weekly.html', context)


@login_required
def reflect_daily(request):
    """
    Vista de revisión diaria
    """
    service = ReflectService(request.user)
    daily = service.get_daily_review()

    context = {
        'title': 'Revisión Diaria',
        'subtitle': daily['day_name'] + ' ' + daily['date'].strftime('%d/%m/%Y'),
        'daily': daily,
    }

    return render(request, 'gtd/reflect/daily.html', context)


@login_required
def reflect_monthly(request):
    """
    Vista de revisión mensual
    """
    service = ReflectService(request.user)
    monthly = service.get_monthly_review()

    context = {
        'title': 'Revisión Mensual',
        'subtitle': monthly['period']['month'],
        'monthly': monthly,
    }

    return render(request, 'gtd/reflect/monthly.html', context)


@login_required
def reflect_audit(request):
    """
    Vista de auditoría del sistema
    """
    service = ReflectService(request.user)
    audit = service.audit_system()

    context = {
        'title': 'Auditoría del Sistema',
        'subtitle': 'Verifica la integridad de tu sistema GTD',
        'audit': audit,
        'issues': audit['issues'],
        'health_score': audit['health_score'],
        'stats': audit['stats'],
    }

    return render(request, 'gtd/reflect/audit.html', context)


# ============ API ENDPOINTS ============

@login_required
@require_http_methods(["GET"])
def reflect_stats_api(request):
    """
    API endpoint para estadísticas de reflexión
    """
    from datetime import date, datetime
    from django.db.models import QuerySet

    def _serialize_for_json(obj):
        if isinstance(obj, dict):
            return {k: _serialize_for_json(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [_serialize_for_json(item) for item in obj]
        if isinstance(obj, (datetime,)):
            return obj.isoformat()
        if isinstance(obj, date):
            return obj.isoformat()
        if isinstance(obj, QuerySet):
            return [str(item) for item in obj]
        if hasattr(obj, 'pk'):
            return f"{obj.__class__.__name__}:{obj.pk}"
        return obj

    service = ReflectService(request.user)
    stats = {
        'weekly': _serialize_for_json(service.get_weekly_review()['stats_summary']),
        'daily': _serialize_for_json(service.get_daily_review()),
        'audit': _serialize_for_json(service.audit_system()),
    }

    return JsonResponse({
        'success': True,
        'stats': stats,
        'timestamp': timezone.now().isoformat()
    })


@login_required
@require_http_methods(["POST"])
def reflect_mark_reviewed(request):
    """
    Marca items como revisados durante la revisión
    """
    item_type = request.POST.get('type')
    item_ids = request.POST.getlist('ids[]')

    if not item_type or not item_ids:
        return JsonResponse({
            'success': False,
            'error': 'Se requiere tipo y IDs'
        })

    try:
        # Marcar items como revisados (actualizar updated_at)
        if item_type == 'task':
            Task.objects.filter(id__in=item_ids, host=request.user).update(
                updated_at=timezone.now()
            )
        elif item_type == 'project':
            Project.objects.filter(id__in=item_ids, host=request.user).update(
                updated_at=timezone.now()
            )
        elif item_type == 'inbox':
            from events.models import InboxItem
            InboxItem.objects.filter(id__in=item_ids, created_by=request.user).update(
                updated_at=timezone.now()
            )

        return JsonResponse({
            'success': True,
            'message': f'{len(item_ids)} items marcados como revisados'
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })
