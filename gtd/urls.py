from django.urls import path
from .views import capture, clarify, organize, reflect, engage, admin_panel

app_name = 'gtd'

urlpatterns = [
    # ============================================
    # ETAPA 1: CAPTURA (Capture)
    # ============================================
    path('inbox/', capture.capture_inbox, name='capture_inbox'),
    path('inbox/quick-add/', capture.capture_quick_add, name='capture_quick_add'),
    path('inbox/bulk/', capture.capture_bulk, name='capture_bulk'),
    path('inbox/stats/', capture.capture_stats_api, name='capture_stats'),
    path('inbox/<int:item_id>/delete/', capture.delete_inbox_item, name='delete_inbox_item'),
    path('inbox/<int:item_id>/done/', capture.inbox_done, name='inbox_done'),
    # En la sección de Captura, agregar:
    path('inbox/submit/', capture.capture_submit_ajax, name='capture_submit_ajax'),
    # ============================================
    # ETAPA 2: CLARIFICAR (Clarify)
    # ============================================
    path('clarify/', clarify.clarify_inbox, name='clarify_inbox'),
    path('clarify/<int:item_id>/process/', clarify.clarify_process_item, name='clarify_process_item'),
    path('clarify/bulk/', clarify.clarify_bulk, name='clarify_bulk'),
    path('clarify/stats/', clarify.clarify_stats_api, name='clarify_stats'),
    path('clarify/<int:item_id>/suggest/', clarify.clarify_suggest_action, name='clarify_suggest'),
    path('inbox/<int:item_id>/process/', clarify.clarify_process_item, name='clarify_process'),

    # ============================================
    # ETAPA 3: ORGANIZAR (Organize)
    # ============================================
    path('organize/', organize.organize_dashboard, name='organize_dashboard'),
    path('organize/next-actions/', organize.organize_next_actions, name='organize_next_actions'),
    path('organize/projects/', organize.organize_projects, name='organize_projects'),
    path('organize/projects/<int:project_id>/', organize.organize_project_detail, name='organize_project_detail'),
    path('organize/waiting/', organize.organize_waiting, name='organize_waiting'),
    path('organize/someday/', organize.organize_someday, name='organize_someday'),
    path('organize/references/', organize.organize_references, name='organize_references'),
    path('organize/calendar/', organize.organize_calendar, name='organize_calendar'),
    path('organize/stats/', organize.organize_stats_api, name='organize_stats'),
    path('organize/task/<int:task_id>/move/', organize.organize_move_task, name='organize_move_task'),
    path('organize/bulk-update/', organize.organize_bulk_update, name='organize_bulk_update'),

    # ============================================
    # ETAPA 4: REFLEXIONAR (Reflect)
    # ============================================
    path('reflect/', reflect.reflect_dashboard, name='reflect_dashboard'),
    path('reflect/weekly/', reflect.reflect_weekly, name='reflect_weekly'),
    path('reflect/daily/', reflect.reflect_daily, name='reflect_daily'),
    path('reflect/monthly/', reflect.reflect_monthly, name='reflect_monthly'),
    path('reflect/audit/', reflect.reflect_audit, name='reflect_audit'),
    path('reflect/stats/', reflect.reflect_stats_api, name='reflect_stats'),
    path('reflect/mark-reviewed/', reflect.reflect_mark_reviewed, name='reflect_mark_reviewed'),

    # ============================================
    # ETAPA 5: EJECUTAR (Engage)
    # ============================================
    path('engage/', engage.engage_dashboard, name='engage_dashboard'),
    path('engage/context/<str:context>/', engage.engage_context, name='engage_context'),
    path('engage/time/<int:minutes>/', engage.engage_by_time, name='engage_by_time'),
    path('engage/energy/<str:level>/', engage.engage_by_energy, name='engage_by_energy'),
    path('engage/today/', engage.engage_today, name='engage_today'),
    path('engage/stats/', engage.engage_stats_api, name='engage_stats'),

    # ============================================
    # ADMINISTRACIÓN
    # ============================================
    path('admin/', admin_panel.dashboard, name='admin_dashboard'),
]
