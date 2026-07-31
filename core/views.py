from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Count, Q
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.contrib.admin.models import LogEntry
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.core.cache import cache
import logging

from events.models import Event, Project, Task
from .models import Article
from .utils import (
    validate_time_parameters,
    get_cached_basic_stats,
    get_cached_status_counts,
    get_recent_activities,
    get_recent_items,
    get_cached_categories,
    generate_home_alerts,
    get_all_apps_url_structure,
    get_app_url_structure
)

logger = logging.getLogger(__name__)

@login_required
def home_view(request, days=None, days_ago=None):
    """Main dashboard view with optimized queries."""
    # Validate parameters
    days, days_ago, start_date, end_date = validate_time_parameters(days, days_ago)
    logger.info(f' d, da[ {validate_time_parameters(days, days_ago)}')

    # Get cached data
    basic_stats = get_cached_basic_stats(start_date, end_date, days, days_ago)
    status_counts = get_cached_status_counts()
    recent_activities = get_recent_activities()
    recent_items = get_recent_items()
    categories = get_cached_categories()
    
    # Generate alerts
    alerts = generate_home_alerts(request.user, {
        'total_events': basic_stats['total_events'],
        'total_projects': basic_stats['total_projects'],
        'total_tasks': basic_stats['total_tasks'],
        'active_projects': status_counts['active_projects'],
        'pending_tasks': status_counts['pending_tasks'],
        'in_progress_tasks': status_counts['in_progress_tasks'],
        'upcoming_events': recent_items['upcoming_events'].count(),
        'recent_activities': len(recent_activities)
    })
    
    context = {
        'page_title': 'Dashboard',
        'days': days,
        'days_ago': days_ago,
        'start_date': start_date,
        'end_date': end_date,
        
        # Statistics
        **basic_stats,
        **status_counts,
        
        # Recent data
        'recent_activities': recent_activities,
        'upcoming_events': recent_items['upcoming_events'],
        'upcoming_events_count': recent_items['upcoming_events'].count(),
        'recent_projects_list': recent_items['recent_projects_list'],
        'recent_tasks': recent_items['recent_tasks'],
        
        # Categories
        'event_categories': categories['event_categories'],
        'project_categories': categories['project_categories'],
        
        # Alerts
        'alerts': alerts,
        
        # User data
        'profile_completion': 50,  # Placeholder
    }
    
    return render(request, 'home/home.html', context)


# Static pages
def about_view(request):
    return render(request, 'about/about.html', {'page_title': 'About'})

def contact_view(request):
    return render(request, 'contact/contact.html', {'page_title': 'Contact'})

def faq_view(request):
    return render(request, 'faq/faq.html', {'page_title': 'FAQ'})

def gtd_guide_view(request):
    return render(request, 'docs/gtd_guide.html', {
        'page_title': 'GTD Guide',
        'title': 'GTD Processing Guide',
        'subtitle': 'Learn to use the inbox processing system efficiently'
    })

def blank_view(request):
    return render(request, 'blank/blank.html', {
        'page_title': 'Blank Page',
        'message': 'Add your content here.'
    })


# AJAX endpoints
@require_GET
@login_required
def load_more_activities(request):
    """Load more recent activities."""
    try:
        offset = int(request.GET.get('offset', 10))
        limit = min(int(request.GET.get('limit', 10)), 50)
        
        content_types = ContentType.objects.get_for_models(Event, Project, Task)
        activities = LogEntry.objects.filter(
            content_type__in=content_types.values()
        ).select_related('user', 'content_type').order_by('-action_time')[offset:offset + limit]
        
        action_map = {1: 'Created', 2: 'Updated', 3: 'Deleted'}
        activities_data = [{
            'content_type': log.content_type.model,
            'action': action_map.get(log.action_flag, 'Modified'),
            'user': log.user.username if log.user else 'System',
            'timestamp': log.action_time.isoformat(),
            'object_repr': log.object_repr,
            'badge_color': 'success' if log.action_flag == 1 else 'primary'
        } for log in activities]
        
        return JsonResponse({
            'success': True,
            'activities': activities_data,
            'has_more': len(activities_data) == limit
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_GET
@login_required
def load_more_recent_items(request, item_type):
    """Load more recent items of specific type."""
    try:
        offset = int(request.GET.get('offset', 5))
        limit = min(int(request.GET.get('limit', 5)), 20)
        
        if item_type == 'projects':
            items = Project.objects.select_related(
                'project_status', 'host', 'assigned_to'
            ).order_by('-updated_at')[offset:offset + limit]
            
            items_data = [{
                'id': item.id,
                'title': item.title,
                'status': item.project_status.status_name if item.project_status else 'Unknown',
                'host': item.host.username if item.host else 'Unassigned',
                'assigned_to': item.assigned_to.username if item.assigned_to else 'Unassigned',
                'updated_at': item.updated_at.isoformat()
            } for item in items]
            
        elif item_type == 'tasks':
            items = Task.objects.select_related(
                'task_status', 'project', 'assigned_to'
            ).order_by('-updated_at')[offset:offset + limit]
            
            items_data = [{
                'id': item.id,
                'title': item.title,
                'status': item.task_status.status_name if item.task_status else 'Unknown',
                'project': item.project.title if item.project else 'No Project',
                'assigned_to': item.assigned_to.username if item.assigned_to else 'Unassigned',
                'updated_at': item.updated_at.isoformat()
            } for item in items]
            
        elif item_type == 'events':
            items = Event.objects.select_related('event_status').filter(
                created_at__gte=timezone.now()
            ).order_by('created_at')[offset:offset + limit]
            
            items_data = [{
                'id': item.id,
                'title': item.title,
                'status': item.event_status.status_name if item.event_status else 'Unknown',
                'created_at': item.created_at.isoformat(),
                'venue': item.venue or 'TBD'
            } for item in items]
            
        else:
            return JsonResponse({'success': False, 'error': f'Invalid type: {item_type}'}, status=400)
        
        return JsonResponse({
            'success': True,
            'items': items_data,
            'has_more': len(items_data) == limit,
            'item_type': item_type
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_GET
@login_required
def load_more_categories(request, category_type):
    """Load more categories."""
    try:
        offset = int(request.GET.get('offset', 10))
        limit = min(int(request.GET.get('limit', 10)), 50)
        
        if category_type == 'events':
            categories = Event.objects.values('event_category').annotate(
                count=Count('id')
            ).order_by('-count')[offset:offset + limit]
            
            categories_data = [{
                'name': cat['event_category'] or 'Uncategorized',
                'count': cat['count']
            } for cat in categories]
            
        elif category_type == 'projects':
            try:
                from events.models import Classification
                categories = Classification.objects.all()[offset:offset + limit]
                categories_data = [{
                    'id': cat.id,
                    'name': cat.name,
                    'description': cat.description or ''
                } for cat in categories]
            except:
                categories_data = []
        else:
            return JsonResponse({'success': False, 'error': f'Invalid type: {category_type}'}, status=400)
        
        return JsonResponse({
            'success': True,
            'categories': categories_data,
            'has_more': len(categories_data) == limit,
            'category_type': category_type
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_POST
@login_required
def refresh_dashboard_data(request):
    """Refresh dashboard data."""
    try:
        data_type = request.POST.get('data_type', 'all')
        days = int(request.POST.get('days', 30))
        days_ago = request.POST.get('days_ago')
        
        _, _, start_date, end_date = validate_time_parameters(days, days_ago)
        
        response_data = {}
        
        if data_type in ['all', 'stats']:
            response_data['stats'] = get_cached_basic_stats(start_date, end_date, days, days_ago)
        
        if data_type in ['all', 'status_counts']:
            response_data['status_counts'] = get_cached_status_counts()
        
        if data_type in ['all', 'activities']:
            response_data['activities'] = get_recent_activities()
        
        return JsonResponse({
            'success': True,
            'data': response_data,
            'refreshed_at': timezone.now().isoformat()
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_GET
@login_required
def get_dashboard_stats(request):
    """Get real-time dashboard statistics."""
    try:
        days = int(request.GET.get('days', 30))
        days_ago = request.GET.get('days_ago')
        
        _, _, start_date, end_date = validate_time_parameters(days, days_ago)
        
        basic_stats = get_cached_basic_stats(start_date, end_date, days, days_ago)
        status_counts = get_cached_status_counts()
        
        total_items = basic_stats['total_events'] + basic_stats['total_projects'] + basic_stats['total_tasks']
        completion_rate = 0
        
        if total_items > 0:
            completed_items = (
                status_counts['completed_events'] +
                status_counts['completed_projects'] +
                status_counts['completed_tasks_count']
            )
            completion_rate = (completed_items / total_items) * 100
        
        return JsonResponse({
            'success': True,
            'stats': {
                'basic': basic_stats,
                'status': status_counts,
                'derived': {
                    'total_items': total_items,
                    'completion_rate': round(completion_rate, 2),
                }
            },
            'timestamp': timezone.now().isoformat()
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# Utility views
@login_required
def search_view(request):
    """Search across all models."""
    query = request.GET.get('query', '').strip()
    results = {}
    
    if query:
        results['articles'] = Article.objects.filter(
            Q(title__icontains=query) | 
            Q(content__icontains=query) |
            Q(excerpt__icontains=query)
        ).order_by('-publication_date')
        
        results['events'] = Event.objects.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(venue__icontains=query) |
            Q(event_category__icontains=query)
        ).select_related('event_status').order_by('-created_at')
        
        results['projects'] = Project.objects.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query)
        ).select_related('project_status').order_by('-created_at')
        
        results['tasks'] = Task.objects.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query)
        ).select_related('task_status').order_by('-created_at')
    
    total_results = sum(results.get(c, []).count() for c in ['articles', 'events', 'projects', 'tasks'])
    
    return render(request, 'search/search.html', {
        'page_title': 'Search Results',
        'query': query,
        'results': results,
        'total_results': total_results,
        'has_results': total_results > 0
    })


def url_map_view(request):
    """Display URL structure."""
    app_name = request.GET.get("app_name", "")
    
    if app_name:
        app_urls = get_app_url_structure(app_name)
        if app_urls:
            return render(request, 'core/url_map_detail.html', {
                'app_urls': app_urls,
                'app_name': app_name,
            })
        return render(request, 'core/url_map_detail.html', {
            'error': f"App '{app_name}' not found",
            'app_name': app_name,
        })
    
    apps_data = get_all_apps_url_structure()
    return render(request, 'core/url_map.html', {
        'apps_data': apps_data,
    })