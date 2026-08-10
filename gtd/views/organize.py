"""
ETAPA 3: ORGANIZAR (Organize)
Propósito: Estructurar los items clarificados en listas accionables según GTD
"""

import logging
from datetime import datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from events.models import Task, Project
from ..services.organize_service import OrganizeService
from .base import GTDViewMixin

logger = logging.getLogger(__name__)


@login_required
def organize_dashboard(request):
    """
    Vista principal de organización GTD
    """
    service = OrganizeService(request.user)
    stats = service.get_organize_stats()
    
    next_actions = service.get_next_actions(limit=20)
    projects = service.get_projects(limit=20)
    waiting = service.get_waiting_for()
    someday = service.get_someday_maybe()
    
    context = {
        'title': 'Organizar GTD',
        'subtitle': 'Estructura tus items en listas accionables',
        'stats': stats,
        'next_actions': next_actions,
        'projects': projects,
        'waiting': waiting,
        'someday': someday,
    }
    
    return render(request, 'gtd/organize/dashboard.html', context)


@login_required
def organize_next_actions(request):
    """
    Vista de próximas acciones organizadas por contexto
    """
    context_filter = request.GET.get('context')
    service = OrganizeService(request.user)
    
    next_actions = service.get_next_actions(context=context_filter)
    
    context = {
        'title': 'Próximas Acciones',
        'subtitle': 'Organizadas por contexto (@casa, @trabajo, @llamadas, etc.)',
        'next_actions': next_actions,
        'selected_context': context_filter,
    }
    
    return render(request, 'gtd/organize/next_actions.html', context)


@login_required
def organize_projects(request):
    """
    Vista de proyectos organizados por estado
    """
    status_filter = request.GET.get('status')
    service = OrganizeService(request.user)
    
    projects = service.get_projects(status=status_filter)
    
    context = {
        'title': 'Proyectos',
        'subtitle': 'Organizados por estado de avance',
        'projects': projects,
        'selected_status': status_filter,
    }
    
    return render(request, 'gtd/organize/projects.html', context)


@login_required
def organize_project_detail(request, project_id):
    """
    Detalle de un proyecto específico
    """
    service = OrganizeService(request.user)
    result = service.get_project_detail(project_id)
    
    if not result.get('success'):
        messages.error(request, result.get('error', 'Proyecto no encontrado'))
        return redirect('gtd:organize_projects')
    
    context = {
        'title': result['project'].title,
        'project_data': result,
    }
    
    return render(request, 'gtd/organize/project_detail.html', context)


@login_required
def organize_waiting(request):
    """
    Vista de lista "Esperando" (Waiting For)
    """
    service = OrganizeService(request.user)
    waiting = service.get_waiting_for()
    
    context = {
        'title': 'Esperando',
        'subtitle': 'Tareas delegadas y respuestas pendientes',
        'waiting': waiting,
    }
    
    return render(request, 'gtd/organize/waiting.html', context)


@login_required
def organize_someday(request):
    """
    Vista de lista "Algún día / Quizás"
    """
    service = OrganizeService(request.user)
    someday = service.get_someday_maybe()
    
    context = {
        'title': 'Algún día / Quizás',
        'subtitle': 'Ideas y proyectos para el futuro',
        'someday': someday,
    }
    
    return render(request, 'gtd/organize/someday.html', context)


@login_required
def organize_references(request):
    """
    Vista de referencias archivadas
    """
    search = request.GET.get('search')
    service = OrganizeService(request.user)
    references = service.get_references(search=search)
    
    context = {
        'title': 'Referencias',
        'subtitle': 'Información archivada para consulta futura',
        'references': references,
        'search': search,
    }
    
    return render(request, 'gtd/organize/references.html', context)


@login_required
def organize_calendar(request):
    """
    Vista de agenda/calendario
    """
    start_date_str = request.GET.get('start')
    end_date_str = request.GET.get('end')
    
    start_date = None
    end_date = None
    
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass
    
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass
    
    service = OrganizeService(request.user)
    calendar = service.get_calendar_items(start_date=start_date, end_date=end_date)
    
    context = {
        'title': 'Agenda',
        'subtitle': 'Items con fechas específicas',
        'calendar': calendar,
    }
    
    return render(request, 'gtd/organize/calendar.html', context)


@login_required
@require_http_methods(["GET"])
def organize_stats_api(request):
    service = OrganizeService(request.user)
    stats = service.get_organize_stats()
    
    return JsonResponse({
        'success': True,
        'stats': stats,
        'timestamp': timezone.now().isoformat()
    })


@login_required
@require_http_methods(["POST"])
def organize_move_task(request, task_id):
    try:
        task = Task.objects.get(id=task_id, host=request.user)
    except Task.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Tarea no encontrada'})
    
    target_status = request.POST.get('status')
    target_list = request.POST.get('list')
    
    if not target_status and not target_list:
        return JsonResponse({'success': False, 'error': 'Se requiere un estado o lista destino'})
    
    try:
        from ..models import TaskStatus
        
        if target_list == 'someday':
            status = TaskStatus.objects.get(status_name='Someday')
            task.task_status = status
            task.save()
        elif target_list == 'waiting':
            status = TaskStatus.objects.get(status_name='Waiting')
            task.task_status = status
            task.save()
        elif target_list == 'references':
            status = TaskStatus.objects.get(status_name='Archived')
            task.task_status = status
            task.save()
        elif target_status:
            status = TaskStatus.objects.get(status_name=target_status)
            task.task_status = status
            task.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Tarea "{task.title}" movida exitosamente',
            'task_id': task.id,
            'new_status': task.task_status.status_name
        })
        
    except TaskStatus.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Estado no encontrado'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(["POST"])
def organize_bulk_update(request):
    item_ids = request.POST.getlist('item_ids[]')
    target_status = request.POST.get('status')
    target_list = request.POST.get('list')
    
    if not item_ids:
        return JsonResponse({'success': False, 'error': 'No se seleccionaron items'})
    
    if not target_status and not target_list:
        return JsonResponse({'success': False, 'error': 'Se requiere un estado o lista destino'})
    
    try:
        from ..models import TaskStatus
        
        tasks = Task.objects.filter(id__in=item_ids, host=request.user)
        count = tasks.count()
        
        if target_list == 'someday':
            status = TaskStatus.objects.get(status_name='Someday')
            tasks.update(task_status=status)
        elif target_list == 'waiting':
            status = TaskStatus.objects.get(status_name='Waiting')
            tasks.update(task_status=status)
        elif target_list == 'references':
            status = TaskStatus.objects.get(status_name='Archived')
            tasks.update(task_status=status)
        elif target_status:
            status = TaskStatus.objects.get(status_name=target_status)
            tasks.update(task_status=status)
        
        return JsonResponse({
            'success': True,
            'message': f'{count} tarea(s) actualizada(s) exitosamente',
            'count': count
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


# Alias legacy para compatibilidad
organize_next_actions = organize_next_actions
organize_projects = organize_projects
organize_waiting = organize_waiting
organize_someday = organize_someday
organize_references = organize_references
organize_calendar = organize_calendar
organize_dashboard = organize_dashboard
organize_project_detail = organize_project_detail
