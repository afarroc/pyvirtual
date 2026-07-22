"""
Views para API v1 — Management360

Endpoints:
- GET /api/v1/health/
- GET /api/v1/projects/
- GET /api/v1/projects/{id}/
- GET /api/v1/projects/{project_id}/tasks/
- GET /api/v1/tasks/{task_id}/
- POST /api/v1/tasks/{task_id}/status/
- GET /api/v1/projects/{project_id}/events/
- GET /api/v1/projects/{project_id}/reminders/
- GET /api/v1/inbox/
- POST /api/v1/inbox/{id}/
"""

from datetime import datetime
from typing import Any

from django.core.paginator import InvalidPage, Paginator
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import status as http_status
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.generics import GenericAPIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from events.models import Event, InboxItem, Project, Reminder, Status, Task, TaskStatus
from .serializers import (
    BibliografiaSerializer,
    CourseCategorySerializer,
    CourseSerializer,
    EventSerializer,
    EvaluationSerializer,
    InboxItemSerializer,
    LessonSerializer,
    ModuleSerializer,
    ProjectSerializer,
    ReminderSerializer,
    TaskSerializer,
)


class _PageableMixin:
    """
    Mixin reutilizable para paginación y filtrado acorde a la especificación M360 API v1.
    Parámetros soportados:
    - q: búsqueda por título/descripción
    - limit: tamaño de página (default 20, max 100)
    - offset: desplazamiento inicial
    - from: fecha ISO mínima (creación)
    - to: fecha ISO máxima (creación)
    """

    search_fields: list[str] = []
    date_from_field: str = "created_at"
    date_to_field: str = "created_at"

    def _paginate(self, request: Request, queryset):
        query = request.query_params.get("q", "")
        limit = self._coerce_int(request.query_params.get("limit"), default=20, minimum=1, maximum=100)
        offset = self._coerce_int(request.query_params.get("offset"), default=0, minimum=0, maximum=10000)

        if query:
            q_filter = Q()
            for field in self.search_fields:
                q_filter |= Q(**{f"{field}__icontains": query})
            queryset = queryset.filter(q_filter)

        date_from = self._parse_iso_date(request.query_params.get("from"))
        date_to = self._parse_iso_date(request.query_params.get("to"))

        if date_from:
            filter_kwargs = {f"{self.date_from_field}__gte": datetime.combine(date_from, datetime.min.time())}
            queryset = queryset.filter(**filter_kwargs)
        if date_to:
            filter_kwargs = {f"{self.date_to_field}__lte": datetime.combine(date_to, datetime.max.time())}
            queryset = queryset.filter(**filter_kwargs)

        paginator = Paginator(queryset.order_by("-created_at"), limit)
        try:
            page = paginator.page(int(offset / limit) + 1)
        except InvalidPage:
            page = paginator.page(1)

        start_index = max(page.start_index() - 1, 0)
        end_index = max(page.end_index(), start_index)
        items = queryset[start_index:end_index]

        serializer_class = self.get_serializer_class()
        serializer = serializer_class(items, many=True, context={"request": request})

        return Response({
            "data": serializer.data,
            "meta": {
                "count": paginator.count,
                "limit": limit,
                "offset": offset,
            },
        })

    @staticmethod
    def _coerce_int(raw: str | None, default: int, minimum: int, maximum: int) -> int:
        if raw is None:
            return default
        try:
            value = int(raw)
        except (TypeError, ValueError):
            return default
        return max(minimum, min(value, maximum))

    @staticmethod
    def _parse_iso_date(value: str | None):
        if not value:
            return None
        parsed = parse_date(value)
        return parsed


class HealthAPIView(APIView):
    """
    GET /api/v1/health/
    """

    authentication_classes = []
    permission_classes = []

    def get(self, request: Request, *args, **kwargs) -> Response:
        return Response({
            "status": "ok",
            "version": "1.0.0",
            "timestamp": timezone.now().isoformat(),
        })


class ProjectViewSet(_PageableMixin, ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    search_fields = ["title", "description"]

    def list(self, request: Request, *args, **kwargs) -> Response:
        return self._paginate(request, self.queryset)

    def retrieve(self, request: Request, *args, **kwargs) -> Response:
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def get_serializer_class(self):
        return ProjectSerializer


class TaskViewSet(_PageableMixin, ModelViewSet):
    queryset = Task.objects.select_related("project", "task_status", "assigned_to").all()
    serializer_class = TaskSerializer
    search_fields = ["title", "description"]

    def list(self, request: Request, *args, **kwargs) -> Response:
        project_id = request.query_params.get("project_id")
        if project_id:
            self.queryset = self.queryset.filter(project_id=project_id)
        assigned_to = request.query_params.get("assigned_to")
        if assigned_to:
            self.queryset = self.queryset.filter(assigned_to_id=assigned_to)
        status_param = request.query_params.get("status")
        if status_param:
            self.queryset = self.queryset.filter(task_status__status_name__iexact=status_param)
        return self._paginate(request, self.queryset)

    def retrieve(self, request: Request, *args, **kwargs) -> Response:
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="status")
    def update_status(self, request: Request, *args, **kwargs) -> Response:
        task = self.get_object()
        serializer = self.get_serializer(task, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def get_serializer_class(self):
        return TaskSerializer

    def perform_create(self, serializer):
        if "project" not in serializer.validated_data:
            raise serializers.ValidationError({"project": "El proyecto es obligatorio."})
        if "task_status" not in serializer.validated_data:
            default_status = TaskStatus.objects.filter(active=True).first()
            if default_status:
                serializer.validated_data["task_status"] = default_status
        if "host" not in serializer.validated_data:
            serializer.validated_data["host"] = self.request.user
        if "assigned_to" not in serializer.validated_data:
            serializer.validated_data["assigned_to"] = self.request.user
        serializer.save()

    def perform_update(self, serializer):
        serializer.save()


class EventViewSet(_PageableMixin, ModelViewSet):
    queryset = Event.objects.select_related("event_status", "host", "assigned_to").prefetch_related("tags")
    serializer_class = EventSerializer
    search_fields = ["title", "description", "event_category"]

    def list(self, request: Request, *args, **kwargs) -> Response:
        project_id = request.query_params.get("project_id")
        if project_id:
            self.queryset = self.queryset.filter(project__id=project_id)
        category = request.query_params.get("category")
        if category:
            self.queryset = self.queryset.filter(event_category__iexact=category)
        status = request.query_params.get("status")
        if status:
            self.queryset = self.queryset.filter(event_status__status_name__iexact=status)
        return self._paginate(request, self.queryset)

    def get_serializer_class(self):
        return EventSerializer

    def perform_create(self, serializer):
        if "event_status" not in serializer.validated_data:
            default_status = Status.objects.filter(active=True).first()
            if default_status:
                serializer.validated_data["event_status"] = default_status
        if "host" not in serializer.validated_data:
            serializer.validated_data["host"] = self.request.user
        if "assigned_to" not in serializer.validated_data:
            serializer.validated_data["assigned_to"] = self.request.user
        serializer.save()

    def perform_update(self, serializer):
        serializer.save()


class ReminderViewSet(_PageableMixin, ModelViewSet):
    queryset = Reminder.objects.select_related("created_by", "task", "project", "event").all()
    serializer_class = ReminderSerializer
    search_fields = ["title", "description"]

    def list(self, request: Request, *args, **kwargs) -> Response:
        project_id = request.query_params.get("project_id")
        if project_id:
            self.queryset = self.queryset.filter(project__id=project_id)
        is_sent = request.query_params.get("is_sent")
        if is_sent is not None:
            self.queryset = self.queryset.filter(is_sent=is_sent.lower() in ("true", "1", "yes"))
        return self._paginate(request, self.queryset)

    def get_serializer_class(self):
        return ReminderSerializer


class InboxItemViewSet(_PageableMixin, ModelViewSet):
    queryset = InboxItem.objects.select_related("created_by", "assigned_to").prefetch_related("tags").all()
    serializer_class = InboxItemSerializer
    search_fields = ["title", "description", "notes"]

    def list(self, request: Request, *args, **kwargs) -> Response:
        gtd_category = request.query_params.get("gtd_category")
        if gtd_category:
            self.queryset = self.queryset.filter(gtd_category=gtd_category)
        created_by = request.query_params.get("created_by")
        if created_by:
            self.queryset = self.queryset.filter(created_by_id=created_by)
        return self._paginate(request, self.queryset)

    def partial_update(self, request: Request, *args, **kwargs) -> Response:
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def get_serializer_class(self):
        return InboxItemSerializer


# ======================
# COURSES API v1
# ======================
from courses.models import Course, CourseCategory, Module, Lesson, Evaluation, Bibliografia
from .serializers import CourseCategorySerializer, CourseSerializer, ModuleSerializer, LessonSerializer, EvaluationSerializer, BibliografiaSerializer


class CourseCategoryViewSet(ModelViewSet):
    queryset = CourseCategory.objects.all().order_by("name")
    serializer_class = CourseCategorySerializer
    search_fields = ["name", "description"]

    def list(self, request: Request, *args, **kwargs) -> Response:
        serializer = self.get_serializer(self.queryset, many=True, context={"request": request})
        return Response(serializer.data)

    def get_serializer_class(self):
        return CourseCategorySerializer


class CourseViewSet(_PageableMixin, ModelViewSet):
    queryset = Course.objects.select_related("category", "tutor").all()
    serializer_class = CourseSerializer
    search_fields = ["title", "description"]
    filterset_fields = ["category", "level", "status", "is_published"]

    def list(self, request: Request, *args, **kwargs) -> Response:
        return self._paginate(request, self.queryset)

    def get_serializer_class(self):
        return CourseSerializer


class ModuleViewSet(ModelViewSet):
    queryset = Module.objects.select_related("course").all()
    serializer_class = ModuleSerializer
    search_fields = ["title", "description", "course__title"]

    def list(self, request: Request, *args, **kwargs) -> Response:
        course_id = request.query_params.get("course_id")
        if course_id:
            self.queryset = self.queryset.filter(course_id=course_id)
        serializer = self.get_serializer(self.queryset, many=True, context={"request": request})
        return Response(serializer.data)


class LessonViewSet(ModelViewSet):
    queryset = Lesson.objects.select_related("module__course").all()
    serializer_class = LessonSerializer
    search_fields = ["title", "content", "saberes_esenciales"]

    def list(self, request: Request, *args, **kwargs) -> Response:
        module_id = request.query_params.get("module_id")
        if module_id:
            self.queryset = self.queryset.filter(module_id=module_id)
        serializer = self.get_serializer(self.queryset, many=True, context={"request": request})
        return Response(serializer.data)


class EvaluationViewSet(ModelViewSet):
    queryset = Evaluation.objects.select_related("course").all()
    serializer_class = EvaluationSerializer
    search_fields = ["nombre", "descripcion", "course__title"]

    def list(self, request: Request, *args, **kwargs) -> Response:
        course_id = request.query_params.get("course_id")
        if course_id:
            self.queryset = self.queryset.filter(course_id=course_id)
        serializer = self.get_serializer(self.queryset, many=True, context={"request": request})
        return Response(serializer.data)


class BibliografiaViewSet(ModelViewSet):
    queryset = Bibliografia.objects.select_related("course").all()
    serializer_class = BibliografiaSerializer
    search_fields = ["autor", "titulo", "course__title"]

    def list(self, request: Request, *args, **kwargs) -> Response:
        course_id = request.query_params.get("course_id")
        if course_id:
            self.queryset = self.queryset.filter(course_id=course_id)
        serializer = self.get_serializer(self.queryset, many=True, context={"request": request})
        return Response(serializer.data)
