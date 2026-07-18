from django.urls import path
from . import views

app_name = 'courses'

# ORDEN DE RESOLUCIÓN: Django evalúa de arriba abajo y la PRIMERA coincidencia gana.
# Por eso TODAS las rutas específicas (courses/, docs/, content/, lessons/, dashboard/,
# manage/, admin/, category/, etc.) deben ir ANTES del patrón catch-all <slug:slug>/
# que de lo contrario devoraría cualquier slug (docs, content, lessons, manage, admin...).

urlpatterns = [
    # ======================
    # PÚBLICO (anónimo + auth, is_published)
    # ======================
    path('', views.index, name='index'),
    path('courses/', views.course_list, name='courses_list'),
    path('category/<slug:category_slug>/', views.course_list, name='course_list_by_category'),
    path('docs/', views.courses_docs, name='docs'),

    # Contenido público (CMS visible)
    path('content/public/', views.public_content_blocks, name='public_content_blocks'),
    path('content/public/<slug:slug>/', views.public_content_detail, name='public_content_detail'),

    # Lecciones independientes (catálogo público + gestión, ANTES del catch-all <slug:slug>/)
    path('lessons/', views.standalone_lessons_list, name='standalone_lessons_list'),
    path('lessons/my-lessons/', views.my_standalone_lessons, name='my_standalone_lessons'),
    path('lessons/create/', views.create_standalone_lesson, name='create_standalone_lesson'),
    path('lessons/<slug:slug>/edit/', views.edit_standalone_lesson, name='edit_standalone_lesson'),
    path('lessons/<slug:slug>/delete/', views.delete_standalone_lesson, name='delete_standalone_lesson'),
    path('lessons/<slug:slug>/toggle-published/', views.toggle_lesson_published, name='toggle_lesson_published'),
    path('lessons/<slug:slug>/preview/', views.preview_lesson, name='preview_standalone_lesson'),
    path('lessons/<slug:slug>/', views.standalone_lesson_detail, name='standalone_lesson_detail'),

    # ======================
    # ESTUDIANTE (login)
    # ======================
    path('dashboard/', views.dashboard, name='dashboard'),
    path('lesson/<int:lesson_id>/complete/', views.mark_lesson_complete, name='mark_lesson_complete'),
    path('<int:course_id>/enroll/', views.enroll, name='enroll'),
    path('<int:course_id>/review/', views.add_review, name='add_review'),

    # ======================
    # TUTOR (login + cv)
    # ======================
    path('manage/', views.manage_courses, name='manage_courses'),
    path('manage/create/', views.create_course, name='create_course'),
    path('manage/create/wizard/', views.create_course_wizard, name='create_course_wizard'),
    path('manage/<slug:slug>/edit/', views.edit_course, name='edit_course'),
    path('manage/<slug:slug>/delete/', views.delete_course, name='delete_course'),
    path('manage/<slug:slug>/analytics/', views.course_analytics, name='course_analytics'),
    path('manage/<slug:slug>/content/', views.manage_content, name='manage_content'),

    # Módulos
    path('manage/<slug:slug>/modules/create/', views.create_module, name='create_module'),
    path('manage/<slug:slug>/modules/<int:module_id>/edit/', views.edit_module, name='edit_module'),
    path('manage/<slug:slug>/modules/<int:module_id>/delete/', views.delete_module, name='delete_module'),
    path('manage/<slug:slug>/modules/<int:module_id>/duplicate/', views.duplicate_module, name='duplicate_module'),
    path('manage/<slug:slug>/modules/<int:module_id>/statistics/', views.module_statistics, name='module_statistics'),
    path('manage/<slug:slug>/modules/<int:module_id>/progress/', views.module_progress, name='module_progress'),
    path('manage/<slug:slug>/modules/bulk-actions/', views.bulk_module_actions, name='bulk_module_actions'),
    path('manage/<slug:slug>/modules/reorder/', views.reorder_modules, name='reorder_modules'),

    # Lecciones de módulo
    path('manage/<slug:slug>/modules/<int:module_id>/lessons/create/', views.create_lesson, name='create_lesson'),
    path('manage/<slug:slug>/modules/<int:module_id>/lessons/<int:lesson_id>/edit/', views.edit_lesson, name='edit_lesson'),
    path('manage/<slug:course_slug>/modules/<int:module_id>/lessons/<int:lesson_id>/preview/', views.preview_lesson, name='preview_lesson'),
    path('manage/<slug:slug>/modules/<int:module_id>/lessons/<int:lesson_id>/delete/', views.delete_lesson, name='delete_lesson'),

    path('modules/overview/', views.modules_overview, name='modules_overview'),

    # Categorías
    path('manage/categories/', views.manage_categories, name='manage_categories'),
    path('manage/categories/create/', views.create_category, name='create_category'),
    path('manage/categories/quick-create/', views.quick_create_category, name='quick_create_category'),
    path('manage/categories/<int:category_id>/edit/', views.edit_category, name='edit_category'),
    path('manage/categories/<int:category_id>/delete/', views.delete_category, name='delete_category'),

    # ======================
    # CMS (login)
    # ======================
    path('content/', views.content_manager, name='content_manager'),
    path('content/create/<str:block_type>/', views.create_content_block, name='create_content_block'),
    path('content/create/', views.create_content_block, name='create_content_block_default'),
    path('content/<slug:slug>/edit/', views.edit_content_block, name='edit_content_block'),
    path('content/<slug:slug>/delete/', views.delete_content_block, name='delete_content_block'),
    path('content/<slug:slug>/duplicate/', views.duplicate_content_block, name='duplicate_content_block'),
    path('content/<slug:slug>/preview/', views.preview_content_block, name='preview_content_block'),
    path('content/my-blocks/', views.my_content_blocks, name='my_content_blocks'),
    path('content/featured/', views.featured_content_blocks, name='featured_content_blocks'),
    path('content/<slug:slug>/toggle-featured/', views.toggle_block_featured, name='toggle_block_featured'),
    path('content/<slug:slug>/toggle-public/', views.toggle_block_public, name='toggle_block_public'),

    # ======================

    # ADMIN (is_staff)
    # ======================
    path('admin/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/users/', views.admin_users, name='admin_users'),
    path('admin/users/<int:user_id>/', views.admin_user_detail, name='admin_user_detail'),
    path('admin/users/<int:user_id>/edit/', views.edit_user, name='edit_user'),

    # ======================
    # CATCH-ALL: detalle de curso (debe ir AL FINAL)
    # ======================
    path('<slug:slug>/', views.course_detail, name='course_detail'),
    path('<slug:slug>/learn/', views.course_learning, name='course_learning'),
    path('<slug:slug>/learn/<int:lesson_id>/', views.course_learning, name='course_learning_lesson'),
]

