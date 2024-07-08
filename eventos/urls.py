from django.urls import path
from .import views

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Páginas principales
    path('', views.index, name="index"),
    path('about/', views.about, name="about"),
    path('blank/', views.blank, name="blank"),

    # Eventos
    path('events/', views.events, name="events"),
    path('events/detail/<int:event_id>', views.event_detail, name="event_detail"),
    path('events/create', views.create_event, name="create_event"),
    path('events/delete/<int:event_id>/', views.event_delete, name='event_delete'),    
    path('events/edit/', views.event_edit, name="event_edit"),
    path('events/edit/<int:event_id>', views.event_edit, name="event_edit"),
    path('events/panel/', views.event_panel, name="event_panel"),
    path('events/panel/<int:event_id>', views.event_panel, name="event_panel"),


    # Proyectos
    path('projects/', views.projects, name="projects"),
    path('projects/detail/<int:id>', views.project_detail, name="project_detail"),
    path('projects/create/', views.create_project, name="create_project"),
    path('projects/delete/<int:project_id>', views.project_delete, name="project_delete"),
    path('projects/edit/', views.project_edit, name="project_edit"),
    path('projects/edit/<int:project_id>', views.project_edit, name="project_edit"),
    path('projects/panel/', views.project_panel, name="project_panel"),
    path('projects/panel/<int:project_id>', views.project_panel, name="project_panel"),

    # Tareas
    path('tasks/', views.tasks, name="tasks"),
    path('tasks/<int:task_id>', views.tasks, name="tasks"),
    path('tasks/create/', views.task_create, name="task_create"),
    path('tasks/edit/', views.task_edit, name="task_edit"),
    path('tasks/edit/<int:task_id>', views.task_edit, name="task_edit"),
    path('tasks/delete/<int:task_id>', views.task_delete, name="task_delete"),

    # Cambio de estado y eliminación de eventos
    path('change_event_status/<int:event_id>/', views.change_event_status, name='change_event_status'),
    path('change_project_status/<int:project_id>/', views.change_project_status, name='change_project_status'),

    # Panel
    path('panel/', views.panel, name='panel'),
    path('panel/event_edit/<int:event_id>/', views.event_edit, name='event_edit'),

    # Sesión
    path('accounts/signup/', views.signup, name='signup'),
    path('logout/', views.signout, name='logout'),
    path('accounts/login/', views.signin, name='signin'),

    # Perfil
    path('profile/<int:user_id>', views.ViewProfileView.as_view(), name='profile'),
    path('edit_profile/<int:user_id>', views.ProfileView.as_view(), name='edit_profile'),
    path('create_profile/', views.ProfileView.as_view(), name='create_profile'),
    path('create_profile/<int:user_id>', views.ProfileView.as_view(), name='create_profile'),
    
    # Configuración
    path('configuration/status_list/', views.status_list, name='status_list'),
    path('configuration/edit_status/<int:status_id>/', views.edit_status, name='edit_status'),
    path('configuration/delete_status/<int:status_id>/', views.delete_status, name='delete_status'),
    path('configuration/create_status/', views.create_status, name='create_status'),

    # Document viewer
    path('documents/docsview/', views.document_view, name='docsview'),
    path('delete/<str:file_type>/<int:file_id>/', views.delete_file, name='delete_file'),
    # Url para subir documentos
    path('documents/doc_upload/', views.DocumentUploadView.as_view(), name='document_upload'),
    # Url para subir imágenes
    path('documents/img_upload/', views.ImageUploadView.as_view(), name='image_upload'),
    
    # Url para subir pandas
    path('about/upload/', views.upload_image, name='upload_image'),
    
    # management
    path('management/manager/', views.management, name='manager'),
    path('management/manager/', views.management, name='management'),
    path('update_event/', views.update_event, name='update_event'),

    path('configuration/create_classification/', views.create_Classification, name='create_classification'),
    path('configuration/edit_classification/<int:Classification_id>/', views.edit_Classification, name='edit_classification'),
    path('configuration/delete_classification/<int:Classification_id>/', views.delete_Classification, name='delete_classification'),
    path('configuration/classification_list/', views.Classification_list, name='classification_list'),


]+static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
