# events/urls.py - Versión corregida
from django.urls import path, include
from django.views.generic import RedirectView
from .views import *  # Esto importa TODAS las vistas directamente
from .setup_views import SetupView
from .views.ai_assistant import inbox_ai_summary, inbox_ai_chat
app_name = 'events'  # EV-1: namespace declarado

urlpatterns = [
    # ============================================================================
    # CONFIGURACIÓN Y SETUP
    # ============================================================================
    path('setup/', SetupView.as_view(), name='setup'),
    path('credits/', add_credits, name='add_credits'),  # Sin views.

    # ============================================================================
    # DASHBOARD Y OVERVIEW
    # ============================================================================
    path('root/', root, name='root'),
    path('dashboard/', unified_dashboard, name='unified_dashboard'),
    path('panel/', panel, name='panel'),
    path('management/', management_index, name='management_index'),

    # ============================================================================
    # GESTIÓN DE EVENTOS
    # ============================================================================
    path('events/', events, name='events'),
    path('events/create/', event_create, name='event_create'),
    path('events/<int:event_id>/', event_detail, name='event_detail'),
    path('events/edit/', event_edit, name='event_edit'),
    path('events/<int:event_id>/edit/', event_edit, name='event_edit'),
    path('events/<int:event_id>/delete/', event_delete, name='event_delete'),
    path('events/<int:event_id>/status/', event_status_change, name='event_status_change'),
    path('events/<int:event_id>/assign/', event_assign, name='event_assign'),
    path('events/<int:event_id>/history/', event_history, name='event_history'),
    path('events/panel/', event_panel, name='event_panel'),
    path('events/panel/<int:event_id>/', event_panel, name='event_panel_with_id'),
    path('events/export/', event_export, name='event_export'),
    path('events/bulk-action/', event_bulk_action, name='event_bulk_action'),
    path('events/edit/', event_edit, name='event_edit_no_id'),
    path('events/<int:event_id>/assign-attendee/<int:user_id>/', assign_attendee_to_event, name='assign_attendee_to_event'),

    # ============================================================================
    # GESTIÓN DE PROYECTOS
    # ============================================================================
    path('projects/', projects, name='projects'),
    path('projects/create/', project_create, name='project_create'),
    path('projects/<int:project_id>/', projects, name='projects_with_id'),
    path('projects/<int:project_id>/detail/', project_detail, name='project_detail'),
    path('projects/<int:project_id>/edit/', project_edit, name='project_edit'),
    path('projects/<int:project_id>/delete/', project_delete, name='project_delete'),
    path('projects/<int:project_id>/activate/', project_activate, name='project_activate'),
    path('projects/<int:project_id>/status/', change_project_status, name='change_project_status'),
    path('projects/panel/', project_panel, name='project_panel'),
    path('projects/panel/<int:project_id>/', project_panel, name='project_panel_with_id'),
    path('projects/export/', project_export, name='project_export'),
    path('projects/bulk-action/', project_bulk_action, name='project_bulk_action'),
    path('projects/alerts/ajax/', get_project_alerts_ajax, name='project_alerts_ajax'),

    # ============================================================================
    # GESTIÓN DE TAREAS
    # ============================================================================
    path('tasks/', tasks, name='tasks'),
    path('tasks/create/', task_create, name='task_create'),
    path('tasks/<int:task_id>/', tasks, name='tasks_with_id'),
    path('tasks/<int:task_id>/edit/', task_edit, name='task_edit'),
    path('tasks/<int:task_id>/delete/', task_delete, name='task_delete'),
    path('tasks/<int:task_id>/activate/', task_activate, name='task_activate'),
    path('tasks/<int:task_id>/status/', change_task_status, name='change_task_status'),
    path('tasks/<int:task_id>/dependencies/', task_dependencies, name='task_dependencies'),
    path('tasks/panel/', task_panel, name='task_panel'),
    path('tasks/panel/<int:task_id>/', task_panel, name='task_panel_with_id'),
    path('tasks/export/', task_export, name='task_export'),
    path('tasks/bulk-action/', task_bulk_action, name='task_bulk_action'),
    path('tasks/status/ajax/', task_change_status_ajax, name='task_change_status_ajax'),

    # ============================================================================
    # PROGRAMACIÓN DE TAREAS (RECURRENTES)
    # ============================================================================
    path('tasks/schedules/', task_schedules, name='task_schedules'),
    path('tasks/schedules/create/', create_task_schedule, name='create_task_schedule'),
    path('tasks/schedules/<int:schedule_id>/', task_schedule_detail, name='task_schedule_detail'),
    path('tasks/schedules/<int:pk>/edit/', TaskScheduleEditView.as_view(), name='edit_task_schedule'),
    path('tasks/schedules/<int:schedule_id>/edit/enhanced/', edit_task_schedule, name='edit_task_schedule_enhanced'),
    path('tasks/schedules/<int:schedule_id>/preview/', task_schedule_preview, name='task_schedule_preview'),
    path('tasks/schedules/<int:schedule_id>/delete/', delete_task_schedule, name='delete_task_schedule'),
    path('tasks/schedules/<int:schedule_id>/generate/', generate_schedule_occurrences, name='generate_schedule_occurrences'),
    path('tasks/schedules/admin/', schedule_admin_dashboard, name='schedule_admin_dashboard'),
    path('tasks/schedules/admin/bulk-action/', schedule_admin_bulk_action, name='schedule_admin_bulk_action'),
    path('schedules/users/', user_schedules_panel, name='user_schedules_panel'),
    path('planning/', planning_task, name='planning_task'),
    path('task_programs_calendar/', task_programs_calendar, name='task_programs_calendar'),

    # ============================================================================
    # SISTEMA GTD (GETTING THINGS DONE)
    # ============================================================================
    path('inbox/', inbox_view, name='inbox'),
    path('inbox/process/', process_inbox_item, name='process_inbox_item_mailbox'),
    path('inbox/process/<int:item_id>/', process_inbox_item, name='process_inbox_item'),
    
    # APIs del Inbox
    path('inbox/api/tasks/', get_available_tasks, name='inbox_api_tasks'),
    path('inbox/api/projects/', get_available_projects, name='inbox_api_projects'),
    path('inbox/api/stats/', inbox_stats_api, name='inbox_api_stats'),
    path('inbox/api/creation-options/', get_inbox_creation_options, name='inbox_api_creation_options'),
    path('inbox/api/create-from-inbox/', create_from_inbox_api, name='inbox_api_create_from_inbox'),
    path('inbox/api/assign-item/', assign_inbox_item_api, name='inbox_api_assign_item'),
    
    # Paneles y Administración Inbox
    path('event/inbox/', event_inbox_panel, name='event_inbox_panel'),
    path('panel/inbox/', event_inbox_panel, name='panel_inbox'),
    path('inbox/admin/', inbox_admin_dashboard, name='inbox_admin_dashboard'),
    path('inbox/admin/<int:item_id>/', inbox_item_detail_admin, name='inbox_item_detail_admin'),
    path('inbox/admin/<int:item_id>/classify/', classify_inbox_item_admin, name='classify_inbox_item_admin'),
    path('inbox/admin/<int:item_id>/authorize/', authorize_inbox_item, name='authorize_inbox_item'),
    path('inbox/admin/bulk-action/', inbox_admin_bulk_action, name='inbox_admin_bulk_action'),
    
    # Gestión y Panel GTD
    path('root/bulk-actions/', root_bulk_actions, name='root_bulk_actions'),
    path('root/activate-bot/', activate_bot, name='activate_bot'),
    path('inbox/management/', inbox_management_panel, name='inbox_management_panel'),
    path('inbox/create/', create_inbox_item_api, name='create_inbox_item_api'),
    
    # APIs del Panel de Gestión GTD
    path('inbox/management/api/queue-data/', get_queue_data, name='get_queue_data'),
    path('inbox/management/api/email-queue/', get_email_queue_items, name='get_email_queue_items'),
    path('inbox/management/api/call-queue/', get_call_queue_items, name='get_call_queue_items'),
    path('inbox/management/api/chat-queue/', get_chat_queue_items, name='get_chat_queue_items'),
    path('inbox/management/api/process-queue/', process_queue, name='process_queue'),
    path('inbox/management/api/update-settings/', update_processing_settings, name='update_processing_settings'),
    path('inbox/management/api/assign-agent/', assign_interaction_to_agent, name='assign_interaction_to_agent'),
    path('inbox/management/api/mark-resolved/', mark_interaction_resolved, name='mark_interaction_resolved'),
    
    # Procesamiento de Emails
    path('api/check-new-emails/', check_new_emails_api, name='check_new_emails_api'),
    path('api/process-cx-emails/', process_cx_emails_api, name='process_cx_emails_api'),
    path('inbox/links/check/', inbox_link_checker, name='inbox_link_checker'),

    path('inbox/api/classification-history/<int:item_id>/', get_classification_history, name='get_classification_history'),
    path('inbox/classify/<int:item_id>/', classify_inbox_item_ajax, name='classify_inbox_item_ajax'),
    path('inbox/api/consensus/<int:item_id>/', get_consensus_api, name='get_consensus_api'),

    # Asistente IA GTD
    path('inbox/ai/summary/', inbox_ai_summary, name='inbox_ai_summary'),
    path('inbox/ai/chat/',    inbox_ai_chat,    name='inbox_ai_chat'),

    # ============================================================================
    # HERRAMIENTAS DE PRODUCTIVIDAD
    # ============================================================================
    path('kanban/', kanban_board_unified, name='kanban_board'),
    path('kanban/organized/', kanban_board_unified, name='kanban_board_organized'),
    path('kanban/project/<int:project_id>/', kanban_project, name='kanban_project'),
    path('eisenhower/', eisenhower_matrix, name='eisenhower_matrix'),
    path('eisenhower/move/<int:task_id>/<str:quadrant>/', move_task_eisenhower, name='move_task_eisenhower'),

# ============================================================================
# DEPENDENCIAS DE TAREAS
# ============================================================================
path('dependencies/<int:task_id>/', task_dependencies, name='task_dependencies_list'),
path('dependencies/', task_dependencies, name='task_dependencies_list'),
path('dependencies/create/<int:task_id>/', create_task_dependency, name='create_task_dependency'),
path('dependencies/<int:dependency_id>/delete/', delete_task_dependency, name='delete_task_dependency'),
path('dependencies/graph/<int:task_id>/', task_dependency_graph, name='task_dependency_graph'),

    # ============================================================================
    # PLANTILLAS DE PROYECTOS
    # ============================================================================
    path('templates/', project_templates, name='project_templates'),
    path('templates/create/', create_project_template, name='create_project_template'),
    path('templates/<int:template_id>/', project_template_detail, name='project_template_detail'),
    path('templates/<int:template_id>/edit/', edit_project_template, name='edit_project_template'),
    path('templates/<int:template_id>/delete/', delete_project_template, name='delete_project_template'),
    path('templates/<int:template_id>/use/', use_project_template, name='use_project_template'),

    # ============================================================================
    # RECORDATORIOS Y NOTIFICACIONES
    # ============================================================================
    path('reminders/', reminders_dashboard, name='reminders_dashboard'),
    path('reminders/create/', create_reminder, name='create_reminder'),
    path('reminders/<int:reminder_id>/edit/', edit_reminder, name='edit_reminder'),
    path('reminders/<int:reminder_id>/delete/', delete_reminder, name='delete_reminder'),
    path('reminders/<int:reminder_id>/mark-sent/', mark_reminder_sent, name='mark_reminder_sent'),
    path('reminders/bulk-action/', bulk_reminder_action, name='bulk_reminder_action'),

    # ============================================================================
    # CONFIGURACIÓN Y AJUSTES
    # ============================================================================
    path('configuration/', include([
        path('status/', status, name='status'),
        path('status/create/', status_create, name='status_create'),
        path('status/create/<int:model_id>/', status_create, name='status_create_with_model'),
        path('status/edit/', status_edit, name='status_edit'),
        path('status/edit/<int:model_id>/', status_edit, name='status_edit_with_model'),
        path('status/edit/<int:model_id>/<int:status_id>/', status_edit, name='status_edit_with_id'),
        path('status/delete/<int:model_id>/', status_delete, name='status_delete_model'),
        path('status/delete/<int:model_id>/<int:status_id>/', status_delete, name='status_delete'),
        path('classifications/', Classification_list, name='classification_list'),
        path('classifications/create/', create_Classification, name='create_classification'),
        path('classifications/<int:classification_id>/edit/', edit_Classification, name='edit_classification'),
        path('classifications/<int:classification_id>/delete/', delete_Classification, name='delete_classification'),
    ])),

    # ============================================================================
    # VISTAS DE TEST Y DESARROLLO
    # ============================================================================
    path('test-board/', test_board, name='test_board'),
    path('test-board/<int:id>/', test_board, name='test_board_with_id'),

    # ============================================================================
    # RUTAS LEGACY (compatibilidad hacia atrás)
    # ============================================================================
    path('unified_dashboard/', unified_dashboard, name='unified_dashboard_alt'),
    path('management/events/', events, name='management_events'),
    path('management/projects/', projects, name='management_projects'),
    path('management/tasks/', tasks, name='management_tasks'),
    path('events/assign/', event_assign, name='event_assign_no_id'),
    path('events/history/', event_history, name='event_history_no_id'),
    path('projects/activate/', project_activate, name='project_activate_no_id'),
    path('projects/edit/', project_edit, name='project_edit_no_id'),
    path('tasks/activate/', task_activate, name='task_activate_no_id'),
    path('tasks/edit/', task_edit, name='task_edit_no_id'),
    path('tasks/create/<int:project_id>/', task_create, name='task_create_with_project'),
    path('tasks/<int:project_id>/', tasks, name='tasks_with_project_id'),
    path('configuration/status/create/', status_create, name='status_create_no_model'),
    path('configuration/status/edit/', status_edit, name='status_edit_no_model'),
    path('configuration/status/delete/<int:model_id>/', status_delete, name='status_delete_no_status_id'),
]

# Redirecciones GTD hacia la nueva app gtd
urlpatterns += [
    path('inbox/', RedirectView.as_view(pattern_name='gtd:capture_inbox', permanent=False)),
    path('inbox/process/', RedirectView.as_view(pattern_name='gtd:clarify_process', permanent=False)),
    path('inbox/process/<int:item_id>/', RedirectView.as_view(pattern_name='gtd:clarify_process', permanent=False)),
]
