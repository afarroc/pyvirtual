"""
ETAPA 1: CAPTURA (Capture)
Principio GTD: "Tu mente es para tener ideas, no para retenerlas"
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import models, transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from events.models import InboxItem, InboxItemHistory
from ..services.capture_service import CaptureService
from .base import GTDViewMixin

logger = logging.getLogger(__name__)


class CaptureViewMixin(GTDViewMixin):
    """Mixin para vistas de captura"""
    
    def get_inbox_items(self, user, filters: Optional[Dict] = None):
        """Obtiene items del inbox con filtros"""
        queryset = InboxItem.objects.filter(
            models.Q(created_by=user) | 
            models.Q(assigned_to=user) |
            models.Q(authorized_users=user)
        ).distinct().select_related('created_by', 'assigned_to')
        
        if filters:
            if filters.get('is_processed') is not None:
                queryset = queryset.filter(is_processed=filters['is_processed'])
            if filters.get('gtd_category'):
                queryset = queryset.filter(gtd_category=filters['gtd_category'])
            if filters.get('priority'):
                queryset = queryset.filter(priority=filters['priority'])
                
        return queryset


@login_required
def capture_inbox(request):
    """
    📥 Vista principal de captura GTD
    Propósito: Vaciar la mente registrando todo lo que llama la atención
    """
    return _render_capture_view(request)


@login_required
@require_http_methods(["POST"])
def capture_submit_ajax(request):
    """
    📤 Endpoint AJAX para capturar items sin recargar la página
    """
    title = request.POST.get('title', '').strip()
    description = request.POST.get('description', '').strip()
    priority = request.POST.get('priority', 'media')
    
    if not title:
        return JsonResponse({
            'success': False,
            'error': 'El título es obligatorio'
        })
    
    try:
        service = CaptureService(request.user)
        inbox_item = service.capture_item(
            title=title,
            description=description,
            priority=priority
        )
        
        # Registrar en historial
        InboxItemHistory.objects.create(
            inbox_item=inbox_item,
            user=request.user,
            action='captured',
            new_values={
                'title': title,
                'priority': priority
            }
        )
        
        # Obtener estadísticas actualizadas
        stats = service.get_capture_stats()
        stats.update({
            'today': service.get_today_count(),
            'this_week': service.get_week_count(),
            'capture_rate': service.get_capture_rate(),
        })
        
        # Obtener items actualizados
        unprocessed_items = service.get_unprocessed_items(limit=50)
        processed_recent = service.get_processed_items(days=7, limit=20)
        
        # Serializar items para JSON (sin source)
        unprocessed_data = []
        for item in unprocessed_items[:10]:
            unprocessed_data.append({
                'id': item.id,
                'title': item.title,
                'description': item.description,
                'priority': item.priority,
                'created_at': item.created_at.isoformat(),
                'created_at_ago': timezone.now() - item.created_at,
                'is_processed': item.is_processed,
            })
        
        processed_data = []
        for item in processed_recent[:10]:
            processed_data.append({
                'id': item.id,
                'title': item.title,
                'processed_at': item.processed_at.isoformat() if item.processed_at else None,
                'processed_at_ago': timezone.now() - item.processed_at if item.processed_at else None,
                'processed_to': str(item.processed_to) if item.processed_to else None,
            })
        
        return JsonResponse({
            'success': True,
            'message': f'✅ Item "{title}" capturado exitosamente',
            'item_id': inbox_item.id,
            'item': {
                'id': inbox_item.id,
                'title': inbox_item.title,
                'created_at': inbox_item.created_at.isoformat(),
                'priority': inbox_item.priority,
                'description': inbox_item.description,
            },
            'stats': stats,
            'unprocessed_count': stats['unprocessed'],
            'processed_count': stats['processed'],
            'unprocessed_items': unprocessed_data,
            'processed_items': processed_data,
        })
        
    except Exception as e:
        logger.error(f"Error capturando item: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


def _render_capture_view(request):
    """Renderiza la vista de captura con estadísticas y lista de items"""
    service = CaptureService(request.user)
    
    # Obtener estadísticas
    stats = service.get_capture_stats()
    
    # Obtener items no procesados (captura reciente)
    unprocessed_items = service.get_unprocessed_items(limit=50)
    
    # Items procesados recientes (historial)
    processed_recent = service.get_processed_items(days=7, limit=20)
    
    # Agregar estadísticas adicionales
    stats.update({
        'today': service.get_today_count(),
        'this_week': service.get_week_count(),
        'capture_rate': service.get_capture_rate(),
    })
    
    context = {
        'title': '📥 Captura GTD - Inbox',
        'subtitle': 'Vacía tu mente. Todo lo que capturas aquí será procesado después.',
        
        # Estadísticas
        'stats': stats,
        'unprocessed_count': stats['unprocessed'],
        'processed_count': stats['processed'],
        'total_count': stats['total'],
        
        # Items
        'unprocessed_items': unprocessed_items,
        'processed_items': processed_recent,
        
        # Opciones de captura
        'priority_options': ['baja', 'media', 'alta'],
        
        # Configuración
        'quick_capture_enabled': True,
        'voice_capture_enabled': False,
        'email_capture_enabled': True,
    }
    
    return render(request, 'gtd/capture/inbox.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def capture_quick_add(request):
    """
    ⚡ Captura rápida desde cualquier parte de la app
    Endpoint para agregar items rápidamente vía AJAX
    """
    title = request.GET.get('title', '').strip() or request.POST.get('title', '').strip()
    description = request.GET.get('description', '').strip() or request.POST.get('description', '').strip()
    
    if not title:
        return JsonResponse({
            'success': False,
            'error': 'El título es obligatorio'
        })
    
    try:
        service = CaptureService(request.user)
        item = service.capture_item(
            title=title,
            description=description
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Item capturado rápidamente',
            'item_id': item.id,
            'item_title': item.title
        })
        
    except Exception as e:
        logger.error(f"Error en captura rápida: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@require_http_methods(["POST"])
def capture_bulk(request):
    """
    📦 Captura masiva de items
    Permite capturar múltiples items de una vez
    """
    items_data = request.POST.getlist('items[]')
    
    if not items_data:
        return JsonResponse({
            'success': False,
            'error': 'No se proporcionaron items para capturar'
        })
    
    try:
        service = CaptureService(request.user)
        captured_items = []
        
        with transaction.atomic():
            for item_data in items_data:
                # Esperamos datos en formato: "Título|Descripción|Prioridad"
                parts = item_data.split('|')
                title = parts[0].strip()
                description = parts[1].strip() if len(parts) > 1 else ''
                priority = parts[2].strip() if len(parts) > 2 else 'media'
                
                if title:
                    item = service.capture_item(
                        title=title,
                        description=description,
                        priority=priority
                    )
                    captured_items.append({
                        'id': item.id,
                        'title': item.title
                    })
        
        return JsonResponse({
            'success': True,
            'message': f'Se capturaron {len(captured_items)} items exitosamente',
            'items': captured_items
        })
        
    except Exception as e:
        logger.error(f"Error en captura masiva: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
def capture_stats_api(request):
    """
    📊 API endpoint para estadísticas de captura en tiempo real
    """
    service = CaptureService(request.user)
    stats = service.get_capture_stats()
    
    # Agregar estadísticas adicionales
    stats.update({
        'today': service.get_today_count(),
        'this_week': service.get_week_count(),
        'capture_rate': service.get_capture_rate(),
    })
    
    return JsonResponse({
        'success': True,
        'stats': stats,
        'timestamp': timezone.now().isoformat()
    })


@login_required
@require_http_methods(["POST"])
def inbox_done(request, item_id):
    """
    ✅ Marca un item como "hecho" (Regla de los 2 Minutos)
    """
    try:
        item = get_object_or_404(
            InboxItem,
            id=item_id,
            created_by=request.user
        )
        
        title = item.title
        
        InboxItemHistory.objects.create(
            inbox_item=item,
            user=request.user,
            action='processed',
            new_values={
                'status': 'done_immediately',
                'rule': 'two_minutes',
                'title': title
            }
        )
        
        item.delete()
        
        service = CaptureService(request.user)
        stats = service.get_capture_stats()
        stats.update({
            'today': service.get_today_count(),
            'this_week': service.get_week_count(),
            'capture_rate': service.get_capture_rate(),
        })
        
        return JsonResponse({
            'success': True,
            'message': f'"{title}" completado (Regla de los 2 Minutos)',
            'stats': stats,
            'unprocessed_count': stats['unprocessed'],
            'processed_count': stats['processed'],
        })
        
    except Exception as e:
        logger.error(f"Error marcando item {item_id} como hecho: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@require_http_methods(["POST"])
def delete_inbox_item(request, item_id):
    """
    🗑️ Elimina un item del inbox vía AJAX
    """
    try:
        item = get_object_or_404(
            InboxItem,
            id=item_id,
            created_by=request.user
        )
        
        title = item.title
        item.delete()
        
        service = CaptureService(request.user)
        stats = service.get_capture_stats()
        stats.update({
            'today': service.get_today_count(),
            'this_week': service.get_week_count(),
            'capture_rate': service.get_capture_rate(),
        })
        
        return JsonResponse({
            'success': True,
            'message': f'Item "{title}" eliminado exitosamente',
            'stats': stats,
            'unprocessed_count': stats['unprocessed'],
            'processed_count': stats['processed'],
        })
        
    except Exception as e:
        logger.error(f"Error eliminando item {item_id}: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })