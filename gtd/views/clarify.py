"""
ETAPA 2: CLARIFICAR (Clarify)
Propósito: Procesar items del inbox y decidir su destino según GTD
"""

import logging
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404, reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from events.models import InboxItem, InboxItemHistory, TaskStatus, ProjectStatus, Project, Event
from ..services.clarify_service import ClarifyService
from .base import GTDViewMixin

logger = logging.getLogger(__name__)


@login_required
def clarify_inbox(request):
    """
    Vista principal de clarificación GTD
    """
    pending_items = InboxItem.objects.filter(
        created_by=request.user,
        is_processed=False
    ).order_by('-priority', '-created_at')
    
    service = ClarifyService(request.user)
    stats = service.get_clarification_stats()
    
    context = {
        'title': 'Clarificar Inbox GTD',
        'subtitle': 'Procesa cada item y decide: ¿Es accionable?',
        'pending_items': pending_items,
        'stats': stats,
        'total_pending': pending_items.count(),
    }
    
    return render(request, 'gtd/clarify/clarify.html', context)


@login_required
def clarify_process_item(request, item_id):
    """
    Procesa un item específico del inbox
    """
    item = get_object_or_404(InboxItem, id=item_id, created_by=request.user)
    
    if request.method == 'POST':
        return _handle_clarify_decision(request, item)
    
    service = ClarifyService(request.user)
    stats = service.get_clarification_stats()
    
    from django.contrib.auth import get_user_model
    User = get_user_model()
    available_users = User.objects.filter(is_active=True).exclude(id=request.user.id)[:10]
    
    task_statuses = TaskStatus.objects.all()
    project_statuses = ProjectStatus.objects.all()
    
    existing_projects = Project.objects.filter(host=request.user)[:10]
    existing_events = Event.objects.filter(host=request.user)[:10]
    
    context = {
        'title': f'Clarificar: {item.title}',
        'item': item,
        'stats': stats,
        'available_users': available_users,
        'task_statuses': task_statuses,
        'project_statuses': project_statuses,
        'existing_projects': existing_projects,
        'existing_events': existing_events,
        'gtd_categories': [
            {'value': 'accionable', 'label': 'Accionable'},
            {'value': 'no_accionable', 'label': 'No Accionable'},
        ],
        'action_types': [
            {'value': 'hacer', 'label': 'Hacer', 'category': 'accionable'},
            {'value': 'delegar', 'label': 'Delegar', 'category': 'accionable'},
            {'value': 'posponer', 'label': 'Posponer', 'category': 'accionable'},
            {'value': 'proyecto', 'label': 'Convertir en Proyecto', 'category': 'accionable'},
            {'value': 'archivar', 'label': 'Archivar', 'category': 'no_accionable'},
            {'value': 'eliminar', 'label': 'Eliminar', 'category': 'no_accionable'},
            {'value': 'incubar', 'label': 'Algún día / Quizás', 'category': 'no_accionable'},
            {'value': 'esperar', 'label': 'Esperar información', 'category': 'no_accionable'},
        ],
        'next_items_count': InboxItem.objects.filter(
            created_by=request.user,
            is_processed=False
        ).exclude(id=item.id).count(),
    }
    
    return render(request, 'gtd/clarify/process.html', context)


def _handle_clarify_decision(request, item):
    decision_data = {
        'gtd_category': request.POST.get('gtd_category'),
        'action_type': request.POST.get('action_type'),
        'estimated_time': int(request.POST.get('estimated_time', 0)),
        'important': request.POST.get('important') == 'on',
        'assigned_to_id': request.POST.get('assigned_to'),
        'due_date': request.POST.get('due_date'),
        'start_date': request.POST.get('start_date'),
        'waiting_for': request.POST.get('waiting_for', ''),
    }
    
    service = ClarifyService(request.user)
    result = service.clarify_item(item.id, decision_data)
    
    if result.get('success'):
        messages.success(request, result.get('message', 'Item procesado exitosamente'))
        
        remaining = InboxItem.objects.filter(
            created_by=request.user,
            is_processed=False
        ).count()
        
        stats = service.get_clarification_stats()
        payload = {
            'success': True,
            'message': result.get('message', 'Item procesado'),
            'remaining': remaining,
            'stats': stats,
        }
        
        if remaining > 0:
            next_item = InboxItem.objects.filter(
                created_by=request.user,
                is_processed=False
            ).order_by('-priority', '-created_at').first()
            
            if next_item:
                payload['next_url'] = reverse('gtd:clarify_process_item', kwargs={'item_id': next_item.id})
        else:
            payload['next_url'] = reverse('gtd:clarify_inbox')
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse(payload)
        
        if payload.get('next_url'):
            return redirect(payload['next_url'])
        return redirect('gtd:clarify_inbox')
    else:
        payload = {
            'success': False,
            'error': result.get('error', 'Error al procesar el item'),
        }
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse(payload)
        
        messages.error(request, payload['error'])
        return redirect('gtd:clarify_process_item', item_id=item.id)


@login_required
@require_http_methods(["POST"])
def clarify_bulk(request):
    item_ids = request.POST.getlist('item_ids[]')
    action = request.POST.get('action')
    
    if not item_ids:
        return JsonResponse({'success': False, 'error': 'No se seleccionaron items'})
    
    if not action:
        return JsonResponse({'success': False, 'error': 'No se especificó una acción'})
    
    try:
        service = ClarifyService(request.user)
        results = []
        
        with transaction.atomic():
            for item_id in item_ids:
                try:
                    item = InboxItem.objects.get(id=item_id, created_by=request.user)
                    if not item.is_processed:
                        decision_data = {
                            'gtd_category': 'accionable' if action in ['hacer', 'delegar', 'posponer', 'proyecto'] else 'no_accionable',
                            'action_type': action,
                            'estimated_time': int(request.POST.get('estimated_time', 0)),
                        }
                        result = service.clarify_item(item.id, decision_data)
                        results.append({
                            'item_id': item_id,
                            'success': result.get('success', False),
                            'message': result.get('message', '')
                        })
                except Exception as e:
                    results.append({
                        'item_id': item_id,
                        'success': False,
                        'error': str(e)
                    })
        
        success_count = sum(1 for r in results if r.get('success'))
        
        return JsonResponse({
            'success': True,
            'processed': success_count,
            'total': len(item_ids),
            'results': results
        })
        
    except Exception as e:
        logger.error(f"Error en procesamiento masivo: {e}")
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def clarify_stats_api(request):
    service = ClarifyService(request.user)
    stats = service.get_clarification_stats()
    
    today = timezone.now().date()
    processed_today = InboxItem.objects.filter(
        created_by=request.user,
        is_processed=True,
        processed_at__date=today
    ).count()
    
    stats.update({
        'processed_today': processed_today,
        'pending_high_priority': InboxItem.objects.filter(
            created_by=request.user,
            is_processed=False,
            priority='alta'
        ).count(),
    })
    
    return JsonResponse({
        'success': True,
        'stats': stats,
        'timestamp': timezone.now().isoformat()
    })


@login_required
@require_http_methods(["POST"])
def clarify_suggest_action(request, item_id):
    try:
        item = get_object_or_404(InboxItem, id=item_id, created_by=request.user)
        
        title_lower = item.title.lower()
        description_lower = (item.description or '').lower()
        combined = f"{title_lower} {description_lower}"
        
        suggestions = []
        
        if any(word in combined for word in ['urgente', 'importante', 'ahora', 'pronto']):
            suggestions.append({
                'action': 'hacer',
                'reason': 'Palabras clave de urgencia detectadas',
                'confidence': 80
            })
        
        if any(word in combined for word in ['reunión', 'evento', 'calendario']):
            suggestions.append({
                'action': 'proyecto',
                'reason': 'Sugiere planificación de evento',
                'confidence': 70
            })
        
        if any(word in combined for word in ['delegar', 'asignar', 'enviar a']):
            suggestions.append({
                'action': 'delegar',
                'reason': 'Sugiere delegación',
                'confidence': 75
            })
        
        if any(word in combined for word in ['idea', 'podría', 'quizás', 'tal vez']):
            suggestions.append({
                'action': 'incubar',
                'reason': 'Sugiere incubación para "Algún día"',
                'confidence': 65
            })
        
        if not suggestions:
            suggestions.append({
                'action': 'hacer',
                'reason': 'Acción recomendada por defecto',
                'confidence': 50
            })
        
        return JsonResponse({
            'success': True,
            'suggestions': suggestions,
            'item_id': item.id
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


# Alias de compatibilidad legacy
clarify_process = clarify_process_item
