from django.urls import path
from . import views

urlpatterns = [
    # Main pages
    path('', views.home_view, name='home'),
    path('', views.home_view, name='index'),
    # Nota: ambos names apuntan al mismo path. Por ahora se mantienen
    # porque muchos templates/rutas usan 'index' y varias vistas usan redirect('home').
    # Requiere migración completa de templates para resolver CORE-10 sin riesgo.

    path('about/', views.about_view, name='about'),
    path('contact/', views.contact_view, name='contact'),
    path('faq/', views.faq_view, name='faq'),
    path('gtd-guide/', views.gtd_guide_view, name='gtd_guide'),
    path('blank/', views.blank_view, name='blank'),
    
    # Dynamic homepage with time filters
    path('<int:days>/', views.home_view, name='home_by_days'),
    path('<int:days>/<int:days_ago>/', views.home_view, name='home_by_days_range'),
    
    # Search
    path('search/', views.search_view, name='search'),
    
    # URL Map
    path('url-map/', views.url_map_view, name='url_map'),
    
    # AJAX endpoints
    path('api/activities/more/', views.load_more_activities, name='load_more_activities'),
    path('api/items/<str:item_type>/more/', views.load_more_recent_items, name='load_more_recent_items'),
    path('api/categories/<str:category_type>/more/', views.load_more_categories, name='load_more_categories'),
    path('api/dashboard/refresh/', views.refresh_dashboard_data, name='refresh_dashboard_data'),
    path('api/dashboard/stats/', views.get_dashboard_stats, name='dashboard_stats'),
]