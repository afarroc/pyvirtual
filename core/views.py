from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Count, Q, Avg, Sum
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.admin.models import LogEntry
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.core.cache import cache
from django.db import connection
import logging
from datetime import timedelta

from events.models import Event, Project, Task, Status, ProjectStatus, TaskStatus
from .models import Article

User = get_user_model()
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

# ==========================================
# DASHBOARD VIEWS
# ==========================================

@login_required
def home_view(request, days=None, days_ago=None):
    """
    Main dashboard view with optimized queries and cached data.
    """
    # Validate parameters
    days, days_ago, start_date, end_date = validate_time_parameters(days, days_ago)

    # Get cached data
    basic_stats = get_cached_basic_stats(start_date, end_date, days, days_ago)
    status_counts = get_cached_status_counts()
    recent_activities = get_recent_activities()
    recent_items = get_recent_items()
    categories = get_cached_categories()

    # ========== QUERIES OPTIMIZADAS ==========
    
    # Recent Events with related data
    recent_events = Event.objects.select_related(
        'event_status', 
        'host'
    ).order_by('-created_at')[:5]

    # Event Statuses (active only)
    event_statuses = Status.objects.filter(
        active=True
    ).order_by('status_name')

    # Project Statuses (active only)
    project_statuses = ProjectStatus.objects.filter(
        active=True
    ).order_by('status_name')

    # Active Projects with related data
    active_projects_list = Project.objects.select_related(
        'project_status', 
        'host', 
        'assigned_to'
    ).filter(
        project_status__status_name__in=['In Progress', 'Active', 'Pending']
    ).order_by('-updated_at')[:4]

    # Team Members (active, recent activity)
    team_members = User.objects.filter(
        is_active=True
    ).order_by('-last_login')[:6]

    # Upcoming Events (with status filtering)
    upcoming_events = Event.objects.select_related(
        'event_status', 'host'
    ).filter(
        created_at__gte=timezone.now()
    ).order_by('created_at')[:5]

    # Recent Tasks with related data
    recent_tasks = Task.objects.select_related(
        'task_status', 
        'project', 
        'assigned_to'
    ).order_by('-updated_at')[:5]

    # ========== NORMALIZAR CATEGORÍAS ==========
    
    # Event Categories
    normalized_event_categories = []
    for cat in categories.get('event_categories', []):
        if isinstance(cat, dict):
            normalized_event_categories.append({
                'name': cat.get('event_category') or cat.get('name', 'Uncategorized'),
                'count': cat.get('count', 0),
                'color': cat.get('color', '#7c3aed'),
                'icon': cat.get('icon', 'fa-calendar')
            })
        else:
            normalized_event_categories.append({
                'name': str(cat),
                'count': 0,
                'color': '#7c3aed',
                'icon': 'fa-calendar'
            })

    # Project Categories
    normalized_project_categories = []
    for cat in categories.get('project_categories', []):
        if hasattr(cat, 'nombre'):
            normalized_project_categories.append({
                'name': cat.nombre,
                'description': getattr(cat, 'descripcion', ''),
                'color': getattr(cat, 'color', '#0ea5e9'),
                'id': getattr(cat, 'id', None)
            })
        elif isinstance(cat, dict):
            normalized_project_categories.append({
                'name': cat.get('name', 'Uncategorized'),
                'description': cat.get('description', ''),
                'color': cat.get('color', '#0ea5e9'),
                'id': cat.get('id', None)
            })
        else:
            normalized_project_categories.append({
                'name': str(cat),
                'description': '',
                'color': '#0ea5e9',
                'id': None
            })

    # ========== ESTADÍSTICAS DERIVADAS ==========
    
    # Completion Rate
    total_items = basic_stats.get('total_events', 0) + basic_stats.get('total_projects', 0) + basic_stats.get('total_tasks', 0)
    completed_items = (
        status_counts.get('completed_events', 0) +
        status_counts.get('completed_projects', 0) +
        status_counts.get('completed_tasks_count', 0)
    )
    completion_rate = round((completed_items / total_items * 100), 1) if total_items > 0 else 0

    # Activity Level
    recent_activity_count = len(recent_activities)
    activity_level = 'high' if recent_activity_count > 10 else 'medium' if recent_activity_count > 5 else 'low'

    # Upcoming Events Count
    upcoming_events_count = upcoming_events.count()

    # ========== GENERAR ALERTAS ==========
    
    alerts = generate_home_alerts(request.user, {
        'total_events': basic_stats.get('total_events', 0),
        'total_projects': basic_stats.get('total_projects', 0),
        'total_tasks': basic_stats.get('total_tasks', 0),
        'active_projects': status_counts.get('active_projects', 0),
        'pending_tasks': status_counts.get('pending_tasks', 0),
        'in_progress_tasks': status_counts.get('in_progress_tasks', 0),
        'upcoming_events': upcoming_events_count,
        'recent_activities': recent_activity_count
    })

    # ========== CONTEXT ==========
    
    context = {
        # Page Settings
        'page_title': 'Dashboard',
        'days': days,
        'days_ago': days_ago,
        'start_date': start_date,
        'end_date': end_date,

        # Basic Statistics
        **basic_stats,
        
        # Status Counts
        **status_counts,
        
        # Derived Statistics
        'total_items': total_items,
        'completion_rate': completion_rate,
        'activity_level': activity_level,

        # Recent Data
        'recent_activities': recent_activities,
        'upcoming_events': upcoming_events,
        'upcoming_events_count': upcoming_events_count,
        'recent_projects_list': recent_items.get('recent_projects_list', []),
        'recent_tasks': recent_tasks,

        # Events
        'recent_events': recent_events,
        'event_statuses': event_statuses,

        # Projects
        'active_projects_list': active_projects_list,
        'project_statuses': project_statuses,

        # Team
        'team_members': team_members,

        # Categories
        'event_categories': normalized_event_categories,
        'project_categories': normalized_project_categories,

        # Alerts
        'alerts': alerts,

        # User Data
        'profile_completion': _calculate_profile_completion(request.user),
    }
    
    return render(request, 'pages/home.html', context)

def _calculate_profile_completion(user):
    """Calculate user profile completion percentage."""
    completion = 0
    fields = []
    
    if user.get_full_name() and user.get_full_name().strip():
        fields.append('full_name')
    if user.email and user.email.strip():
        fields.append('email')
    if hasattr(user, 'profile'):
        profile = user.profile
        if hasattr(profile, 'bio') and profile.bio:
            fields.append('bio')
        if hasattr(profile, 'avatar') and profile.avatar:
            fields.append('avatar')
        if hasattr(profile, 'phone') and profile.phone:
            fields.append('phone')
        if hasattr(profile, 'location') and profile.location:
            fields.append('location')
        if hasattr(profile, 'website') and profile.website:
            fields.append('website')
    
    total_fields = 7
    completion = min(100, round((len(fields) / total_fields) * 100))
    return completion


# ==========================================
# STATIC PAGES
# ==========================================

def about_view(request):
    """About page."""
    return render(request, 'about/about.html', {
        'page_title': 'About',
        'company_name': 'Management360',
        'year': timezone.now().year
    })

def contact_view(request):
    """Contact page."""
    return render(request, 'contact/contact.html', {
        'page_title': 'Contact',
        'contact_email': 'support@management360.com'
    })

def faq_view(request):
    """FAQ page."""
    return render(request, 'faq/faq.html', {
        'page_title': 'FAQ',
        'faq_categories': _get_faq_categories()
    })

def gtd_guide_view(request):
    """GTD Guide page."""
    return render(request, 'docs/gtd_guide.html', {
        'page_title': 'GTD Guide',
        'title': 'GTD Processing Guide',
        'subtitle': 'Learn to use the inbox processing system efficiently'
    })

def blank_view(request):
    """Blank page template."""
    return render(request, 'blank/blank.html', {
        'page_title': 'Blank Page',
        'message': 'Add your content here.'
    })


# ==========================================
# AJAX ENDPOINTS
# ==========================================

@require_GET
@login_required
def load_more_activities(request):
    """Load more recent activities with pagination."""
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
            'has_more': len(activities_data) == limit,
            'total': activities.count()
        })
    except Exception as e:
        logger.error(f"Error loading activities: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_GET
@login_required
def load_more_recent_items(request, item_type):
    """Load more recent items of specific type with pagination."""
    try:
        offset = int(request.GET.get('offset', 5))
        limit = min(int(request.GET.get('limit', 5)), 20)
        
        items_data = []
        total_count = 0
        
        if item_type == 'projects':
            items = Project.objects.select_related(
                'project_status', 'host', 'assigned_to'
            ).order_by('-updated_at')[offset:offset + limit]
            
            total_count = Project.objects.count()
            
            items_data = [{
                'id': item.id,
                'title': item.title,
                'status': item.project_status.status_name if item.project_status else 'Unknown',
                'host': item.host.username if item.host else 'Unassigned',
                'assigned_to': item.assigned_to.username if item.assigned_to else 'Unassigned',
                'updated_at': item.updated_at.isoformat(),
                'progress': getattr(item, 'done', False)
            } for item in items]
            
        elif item_type == 'tasks':
            items = Task.objects.select_related(
                'task_status', 'project', 'assigned_to'
            ).order_by('-updated_at')[offset:offset + limit]
            
            total_count = Task.objects.count()
            
            items_data = [{
                'id': item.id,
                'title': item.title,
                'status': item.task_status.status_name if item.task_status else 'Unknown',
                'project': item.project.title if item.project else 'No Project',
                'project_id': item.project.id if item.project else None,
                'assigned_to': item.assigned_to.username if item.assigned_to else 'Unassigned',
                'updated_at': item.updated_at.isoformat(),
                'due_date': item.created_at.isoformat()
            } for item in items]
            
        elif item_type == 'events':
            items = Event.objects.select_related('event_status').filter(
                created_at__gte=timezone.now()
            ).order_by('created_at')[offset:offset + limit]
            
            total_count = Event.objects.count()
            
            items_data = [{
                'id': item.id,
                'title': item.title,
                'status': item.event_status.status_name if item.event_status else 'Unknown',
                'created_at': item.created_at.isoformat(),
                'venue': item.venue or 'TBD',
                'host': item.host.username if item.host else 'Unassigned'
            } for item in items]
            
        else:
            return JsonResponse({'success': False, 'error': f'Invalid type: {item_type}'}, status=400)
        
        return JsonResponse({
            'success': True,
            'items': items_data,
            'has_more': len(items_data) == limit,
            'item_type': item_type,
            'total': total_count,
            'offset': offset + len(items_data)
        })
    except Exception as e:
        logger.error(f"Error loading {item_type}: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_GET
@login_required
def load_more_categories(request, category_type):
    """Load more categories with pagination."""
    try:
        offset = int(request.GET.get('offset', 10))
        limit = min(int(request.GET.get('limit', 10)), 50)
        
        categories_data = []
        total_count = 0
        
        if category_type == 'events':
            categories = Event.objects.values('event_category').annotate(
                count=Count('id')
            ).order_by('-count')[offset:offset + limit]
            
            total_count = Event.objects.values('event_category').distinct().count()
            
            categories_data = [{
                'name': cat['event_category'] or 'Uncategorized',
                'count': cat['count'],
                'color': '#7c3aed'
            } for cat in categories]
            
        elif category_type == 'projects':
            try:
                from events.models import Classification
                categories = Classification.objects.all()[offset:offset + limit]
                total_count = Classification.objects.count()
                
                categories_data = [{
                    'id': cat.id,
                    'name': cat.name,
                    'description': cat.description or '',
                    'color': getattr(cat, 'color', '#0ea5e9'),
                    'count': getattr(cat, 'project_count', 0)
                } for cat in categories]
            except ImportError:
                categories_data = []
                total_count = 0
        else:
            return JsonResponse({'success': False, 'error': f'Invalid type: {category_type}'}, status=400)
        
        return JsonResponse({
            'success': True,
            'categories': categories_data,
            'has_more': len(categories_data) == limit,
            'category_type': category_type,
            'total': total_count,
            'offset': offset + len(categories_data)
        })
    except Exception as e:
        logger.error(f"Error loading categories: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_POST
@login_required
def refresh_dashboard_data(request):
    """Refresh dashboard data with cache invalidation."""
    try:
        data_type = request.POST.get('data_type', 'all')
        days = int(request.POST.get('days', 30))
        days_ago = request.POST.get('days_ago')
        
        _, _, start_date, end_date = validate_time_parameters(days, days_ago)
        
        response_data = {}
        cache_keys = []
        
        if data_type in ['all', 'stats']:
            stats = get_cached_basic_stats(start_date, end_date, days, days_ago)
            response_data['stats'] = stats
            cache_keys.append('dashboard_stats')
        
        if data_type in ['all', 'status_counts']:
            status_counts = get_cached_status_counts()
            response_data['status_counts'] = status_counts
            cache_keys.append('status_counts')
        
        if data_type in ['all', 'activities']:
            activities = get_recent_activities()
            response_data['activities'] = activities
            cache_keys.append('recent_activities')
        
        if data_type in ['all', 'categories']:
            categories = get_cached_categories()
            response_data['categories'] = categories
            cache_keys.append('categories')
        
        # Clear cache for updated keys
        for key in cache_keys:
            cache.delete(key)
        
        return JsonResponse({
            'success': True,
            'data': response_data,
            'refreshed_at': timezone.now().isoformat(),
            'cleared_cache': cache_keys
        })
    except Exception as e:
        logger.error(f"Error refreshing dashboard: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_GET
@login_required
def get_dashboard_stats(request):
    """Get real-time dashboard statistics."""
    try:
        days = int(request.GET.get('days', 30))
        days_ago = request.GET.get('days_ago')
        
        _, _, start_date, end_date = validate_time_parameters(days, days_ago)
        
        # Get stats with cache
        basic_stats = get_cached_basic_stats(start_date, end_date, days, days_ago)
        status_counts = get_cached_status_counts()
        
        # Calculate derived metrics
        total_items = (
            basic_stats.get('total_events', 0) + 
            basic_stats.get('total_projects', 0) + 
            basic_stats.get('total_tasks', 0)
        )
        
        completed_items = (
            status_counts.get('completed_events', 0) +
            status_counts.get('completed_projects', 0) +
            status_counts.get('completed_tasks_count', 0)
        )
        completion_rate = round((completed_items / total_items * 100), 1) if total_items > 0 else 0
        
        # Get recent activity count
        recent_activities = get_recent_activities()
        
        return JsonResponse({
            'success': True,
            'stats': {
                'basic': basic_stats,
                'status': status_counts,
                'derived': {
                    'total_items': total_items,
                    'completion_rate': completion_rate,
                    'recent_activity_count': len(recent_activities)
                }
            },
            'timestamp': timezone.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ==========================================
# SEARCH VIEW
# ==========================================

@login_required
def search_view(request):
    """Search across all models with optimized queries."""
    query = request.GET.get('query', '').strip()
    results = {}
    total_results = 0
    
    if query and len(query) >= 2:
        # Search Articles
        results['articles'] = Article.objects.filter(
            Q(title__icontains=query) | 
            Q(content__icontains=query) |
            Q(excerpt__icontains=query)
        ).order_by('-publication_date')[:10]
        
        # Search Events
        results['events'] = Event.objects.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(venue__icontains=query) |
            Q(event_category__icontains=query)
        ).select_related('event_status').order_by('-created_at')[:10]
        
        # Search Projects
        results['projects'] = Project.objects.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query)
        ).select_related('project_status').order_by('-created_at')[:10]
        
        # Search Tasks
        results['tasks'] = Task.objects.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query)
        ).select_related('task_status', 'project').order_by('-created_at')[:10]
        
        # Calculate total results
        for model_name, queryset in results.items():
            total_results += queryset.count()
    
    return render(request, 'search/search.html', {
        'page_title': 'Search Results',
        'query': query,
        'results': results,
        'total_results': total_results,
        'has_results': total_results > 0,
        'is_searching': bool(query and len(query) >= 2)
    })


# ==========================================
# URL MAP VIEW
# ==========================================

def url_map_view(request):
    """Display URL structure of the application."""
    app_name = request.GET.get("app_name", "")
    
    if app_name:
        app_urls = get_app_url_structure(app_name)
        if app_urls:
            return render(request, 'core/url_map_detail.html', {
                'app_urls': app_urls,
                'app_name': app_name,
                'page_title': f'URL Map - {app_name}'
            })
        return render(request, 'core/url_map_detail.html', {
            'error': f"App '{app_name}' not found",
            'app_name': app_name,
            'page_title': 'URL Map - Not Found'
        })
    
    apps_data = get_all_apps_url_structure()
    return render(request, 'core/url_map.html', {
        'apps_data': apps_data,
        'page_title': 'URL Map',
        'total_apps': len(apps_data)
    })


# ==========================================
# HELPER FUNCTIONS
# ==========================================

def _get_faq_categories():
    """Get FAQ categories with sample data."""
    return [
        {
            'name': 'Getting Started',
            'icon': 'fa-rocket',
            'questions': [
                {'question': 'How do I create an account?', 'answer': '...'},
                {'question': 'What is Management360?', 'answer': '...'}
            ]
        },
        {
            'name': 'Projects',
            'icon': 'fa-folder-open',
            'questions': [
                {'question': 'How do I create a project?', 'answer': '...'},
                {'question': 'How do I assign team members?', 'answer': '...'}
            ]
        },
        {
            'name': 'Tasks',
            'icon': 'fa-list-check',
            'questions': [
                {'question': 'How do I create a task?', 'answer': '...'},
                {'question': 'How do I track task progress?', 'answer': '...'}
            ]
        }
    ]