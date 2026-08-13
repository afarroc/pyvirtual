"""
System Events API views.

Nota de dominio:
- `SystemEvent` = registro de acción del sistema (task_created, project_updated, etc.)
- `Event` = evento de calendario/reunión. Si un SystemEvent apunta a `events.Event`,
  su `content_type` será `event` y su `object_id` el pk del evento de calendario.

Endpoints:
- GET /events/api/system-events/
- GET /events/api/system-events/?action=task_created&user_id=1&limit=50
- GET /events/api/system-events/<int:event_id>/
"""

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib.contenttypes.models import ContentType

from ..models import SystemEvent


def _serialize_system_event(se: SystemEvent):
    return {
        'id': se.pk,
        'action_type': se.action_type,
        'action_display': se.get_action_type_display(),
        'timestamp': se.timestamp.isoformat(),
        'user_id': se.user_id,
        'user': se.user.username if se.user else None,
        'summary': se.summary,
        'metadata': se.metadata or {},
        'content_type': se.content_type.model if se.content_type else None,
        'object_id': se.object_id,
    }


@login_required
def system_events_feed(request):
    """
    Feed ligero de eventos del sistema para dashboards/paneles.
    Query params:
    - action: filtro por action_type exacto
    - user_id: filtro por usuario
    - limit: máximo de registros (default 100, max 500)
    - offset: paginación simple
    """
    try:
        qs = SystemEvent.objects.select_related('user', 'content_type').all()

        action = request.GET.get('action')
        if action:
            qs = qs.filter(action_type=action)

        user_id = request.GET.get('user_id')
        if user_id:
            qs = qs.filter(user_id=user_id)

        limit = int(request.GET.get('limit', 100))
        if limit < 1:
            limit = 100
        if limit > 500:
            limit = 500

        offset = int(request.GET.get('offset', 0))
        qs = qs[offset:offset + limit]

        data = [_serialize_system_event(se) for se in qs]
        return JsonResponse({'count': len(data), 'results': data})
    except Exception as exc:
        return JsonResponse({'error': str(exc)}, status=400)


@login_required
def system_event_detail(request, event_id):
    """
    Detalle de un evento puntual.
    """
    try:
        se = SystemEvent.objects.select_related('user', 'content_type').get(pk=event_id)
        return JsonResponse(_serialize_system_event(se))
    except SystemEvent.DoesNotExist:
        return JsonResponse({'error': 'SystemEvent not found'}, status=404)
    except Exception as exc:
        return JsonResponse({'error': str(exc)}, status=400)


@login_required
def system_events_summary(request):
    """
    Resumen agregado por tipo de acción en una ventana de tiempo.
    Query params:
    - days: ventana en días (default 7)
    """
    try:
        days = int(request.GET.get('days', 7))
        from django.utils import timezone
        from django.db.models import Count
        since = timezone.now() - timezone.timedelta(days=days)

        qs = SystemEvent.objects.filter(timestamp__gte=since)
        summary = (
            qs.values('action_type')
            .annotate(count=Count('id'))
            .order_by('-count')
        )

        result = [
            {
                'action_type': row['action_type'],
                'count': row['count'],
            }
            for row in summary
        ]
        return JsonResponse({'days': days, 'since': since.isoformat(), 'summary': result})
    except Exception as exc:
        return JsonResponse({'error': str(exc)}, status=400)
