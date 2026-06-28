from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    CourseCategoryViewSet,
    CourseViewSet,
    EventViewSet,
    HealthAPIView,
    InboxItemViewSet,
    ProjectViewSet,
    ReminderViewSet,
    TaskViewSet,
)

router = DefaultRouter()
router.register(r'projects', ProjectViewSet, basename='project')
router.register(r'tasks', TaskViewSet, basename='task')
router.register(r'courses', CourseViewSet, basename='course')
router.register(r'course-categories', CourseCategoryViewSet, basename='course-category')
router.register(r'events', EventViewSet, basename='event')
router.register(r'reminders', ReminderViewSet, basename='reminder')
router.register(r'inbox', InboxItemViewSet, basename='inbox')

app_name = 'api_v1'

urlpatterns = [
    path('health/', HealthAPIView.as_view(), name='health'),
    path('', include(router.urls)),
]
