from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    BibliografiaViewSet,
    CourseCategoryViewSet,
    CourseViewSet,
    EventViewSet,
    EvaluationViewSet,
    HealthAPIView,
    InboxItemViewSet,
    LessonViewSet,
    ModuleViewSet,
    ProjectViewSet,
    ReminderViewSet,
    TaskViewSet,
)
from digitalizacion.views import (
    LoteViewSet,
    DocumentoViewSet,
    EtapaViewSet,
    FedatacionViewSet,
)

router = DefaultRouter()
router.register(r'projects', ProjectViewSet, basename='project')
router.register(r'tasks', TaskViewSet, basename='task')
router.register(r'courses', CourseViewSet, basename='course')
router.register(r'course-categories', CourseCategoryViewSet, basename='course-category')
router.register(r'modules', ModuleViewSet, basename='module')
router.register(r'lessons', LessonViewSet, basename='lesson')
router.register(r'evaluations', EvaluationViewSet, basename='evaluation')
router.register(r'bibliografia', BibliografiaViewSet, basename='bibliografia')
router.register(r'events', EventViewSet, basename='event')
router.register(r'reminders', ReminderViewSet, basename='reminder')
router.register(r'inbox', InboxItemViewSet, basename='inbox')
router.register(r'digitalizacion/lotes', LoteViewSet, basename='digitalizacion-lote')
router.register(r'digitalizacion/documentos', DocumentoViewSet, basename='digitalizacion-documento')
router.register(r'digitalizacion/etapas', EtapaViewSet, basename='digitalizacion-etapa')
router.register(r'digitalizacion/fedatacion', FedatacionViewSet, basename='digitalizacion-fedatacion')

app_name = 'api_v1'

urlpatterns = [
    path('health/', HealthAPIView.as_view(), name='health'),
    path('', include(router.urls)),
]
