"""
Serializers para API v1 — Management360

Endpoints consumidos:
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

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers

from events.models import (
    Classification,
    Event,
    InboxItem,
    Project,
    ProjectStatus,
    Reminder,
    Status,
    Task,
    TaskStatus,
    Tag,
)

User = get_user_model()


class _NestedStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Status
        fields = ["id", "status_name", "status_description"]


class _NestedProjectStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectStatus
        fields = ["id", "status_name", "active", "color"]


class _NestedTaskStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskStatus
        fields = ["id", "status_name", "active", "color"]


class _NestedEventStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Status
        fields = ["id", "status_name", "active", "color"]


class _NestedTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name", "color", "description"]


class _NestedUserSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "email"]


class _ProjectStatsSerializer(serializers.Serializer):
    tasks_total = serializers.IntegerField()
    tasks_completed = serializers.IntegerField()
    events_total = serializers.IntegerField()
    reminders_total = serializers.IntegerField()


class ProjectSerializer(serializers.ModelSerializer):
    project_status = _NestedProjectStatusSerializer(read_only=True)
    project_status_id = serializers.PrimaryKeyRelatedField(
        queryset=ProjectStatus.objects.all(), source="project_status", write_only=True, required=False
    )
    status = serializers.CharField(source='project_status.status_name', read_only=True)
    stats = serializers.SerializerMethodField()
    host = _NestedUserSummarySerializer(read_only=True)
    host_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source="host", write_only=True, required=False
    )
    assigned_to = _NestedUserSummarySerializer(read_only=True)
    assigned_to_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source="assigned_to", write_only=True, required=False
    )

    class Meta:
        model = Project
        fields = [
            "id",
            "title",
            "description",
            "status",
            "created_at",
            "updated_at",
            "done",
            "project_status",
            "project_status_id",
            "host",
            "host_id",
            "assigned_to",
            "assigned_to_id",
            "ticket_price",
            "stats",
        ]

    def get_stats(self, obj):
        return {
            "tasks_total": obj.task_set.count() if hasattr(obj, "task_set") else 0,
            "tasks_completed": (
                obj.task_set.filter(done=True).count() if hasattr(obj, "task_set") else 0
            ),
            "events_total": Event.objects.filter(project=obj).count(),
            "reminders_total": Reminder.objects.filter(project=obj).count(),
        }


class TaskSerializer(serializers.ModelSerializer):
    task_status = _NestedTaskStatusSerializer(read_only=True)
    task_status_id = serializers.PrimaryKeyRelatedField(queryset=TaskStatus.objects.all(), source="task_status", write_only=True, required=False)
    status = serializers.CharField(source='task_status.status_name', read_only=True)
    status_id = serializers.IntegerField(source='task_status.id', read_only=True)
    project = serializers.PrimaryKeyRelatedField(read_only=True)
    project_id = serializers.PrimaryKeyRelatedField(queryset=Project.objects.all(), source="project", write_only=True, required=False)
    project_title = serializers.CharField(source="project.title", read_only=True)
    assigned_to = _NestedUserSummarySerializer(read_only=True)
    assigned_to_id = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), source="assigned_to", write_only=True, required=False)
    host = _NestedUserSummarySerializer(read_only=True)
    host_id = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), source="host", write_only=True, required=False)
    tags = _NestedTagSerializer(many=True, read_only=True)

    dependencies = serializers.SerializerMethodField()
    events_linked = serializers.SerializerMethodField()
    reminders_linked = serializers.SerializerMethodField()
    done = serializers.BooleanField(required=False)

    class Meta:
        model = Task
        fields = [
            "id",
            "title",
            "description",
            "status",
            "status_id",
            "task_status",
            "task_status_id",
            "important",
            "assigned_to",
            "assigned_to_id",
            "host",
            "host_id",
            "project",
            "project_id",
            "project_title",
            "event",
            "event_id",
            "tags",
            "created_at",
            "updated_at",
            "dependencies",
            "events_linked",
            "reminders_linked",
            "done",
        ]
        read_only_fields = ["status_id", "event_id", "event"]

    def get_dependencies(self, obj):
        return list(obj.dependencies.values_list("depends_on_id", flat=True))

    def get_events_linked(self, obj):
        if obj.event_id:
            return [obj.event_id]
        return []

    def get_reminders_linked(self, obj):
        return list(obj.reminder_set.values_list("id", flat=True))


class EventSerializer(serializers.ModelSerializer):
    event_status = _NestedEventStatusSerializer(read_only=True)
    event_status_id = serializers.PrimaryKeyRelatedField(
        queryset=Status.objects.all(), source="event_status", write_only=True, required=False
    )
    status = serializers.CharField(source='event_status.status_name', read_only=True)
    host = _NestedUserSummarySerializer(read_only=True)
    host_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source="host", write_only=True, required=False
    )
    assigned_to = _NestedUserSummarySerializer(read_only=True)
    assigned_to_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source="assigned_to", write_only=True, required=False
    )
    tags = _NestedTagSerializer(many=True, read_only=True)

    class Meta:
        model = Event
        fields = [
            "id",
            "title",
            "description",
            "status",
            "event_status",
            "event_status_id",
            "venue",
            "host",
            "host_id",
            "event_category",
            "max_attendees",
            "ticket_price",
            "assigned_to",
            "assigned_to_id",
            "tags",
            "links",
            "classification",
            "created_at",
            "updated_at",
        ]


class ReminderSerializer(serializers.ModelSerializer):
    created_by = _NestedUserSummarySerializer(read_only=True)
    created_by_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source="created_by", write_only=True, required=False
    )

    class Meta:
        model = Reminder
        fields = [
            "id",
            "title",
            "description",
            "remind_at",
            "task",
            "project",
            "event",
            "created_by",
            "created_by_id",
            "is_sent",
            "reminder_type",
            "created_at",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.task_id:
            data["task"] = {"id": instance.task_id, "title": instance.task.title if instance.task else None}
        if instance.project_id:
            data["project"] = {"id": instance.project_id, "title": instance.project.title if instance.project else None}
        if instance.event_id:
            data["event"] = {"id": instance.event_id, "title": instance.event.title if instance.event else None}
        return data


class InboxItemSerializer(serializers.ModelSerializer):
    created_by = _NestedUserSummarySerializer(read_only=True)
    processed_to_summary = serializers.SerializerMethodField()

    class Meta:
        model = InboxItem
        fields = [
            "id",
            "title",
            "description",
            "created_at",
            "created_by",
            "is_processed",
            "processed_at",
            "processed_to_summary",
            "gtd_category",
            "action_type",
            "priority",
            "context",
            "estimated_time",
            "due_date",
            "energy_required",
            "notes",
            "is_public",
            "assigned_to",
        ]

    def get_processed_to_summary(self, obj):
        if not obj.processed_to:
            return None
        return {
            "content_type": obj.processed_to_content_type.model,
            "id": obj.processed_to_object_id,
            "title": str(obj.processed_to),
        }


# ======================
# COURSES API v1
# ======================
from courses.models import Course, CourseCategory

class CourseCategorySerializer(serializers.ModelSerializer):
    courses_count = serializers.SerializerMethodField()

    class Meta:
        model = CourseCategory
        fields = ["id", "name", "description", "slug", "courses_count"]

    def get_courses_count(self, obj):
        return obj.courses.count() if hasattr(obj, 'courses') else 0


class CourseSerializer(serializers.ModelSerializer):
    category = CourseCategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=CourseCategory.objects.all(), source="category", write_only=True, required=False
    )
    tutor = _NestedUserSummarySerializer(read_only=True)
    tutor_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source="tutor", write_only=True, required=False
    )

    class Meta:
        model = Course
        fields = [
            "id", "title", "slug", "description", "short_description",
            "tutor", "tutor_id", "category", "category_id", "level",
            "price", "duration_hours", "students_count", "average_rating",
            "thumbnail", "is_published", "is_featured", "published_at",
            "created_at", "updated_at",
            # Metadatos UPN
            "codigo", "creditos", "ht", "hp", "hl", "pc", "requisitos",
            "naturaleza", "competencia_general", "componentes", "sumilla",
            "logro_curso", "sistema_evaluacion", "bibliografia",
        ]

# ======================
# COURSES EXTENDED API v1
# ======================
from courses.models import Course, CourseCategory, Module, Lesson, Evaluation, Bibliografia

class ModuleSerializer(serializers.ModelSerializer):
    course = serializers.PrimaryKeyRelatedField(queryset=Course.objects.all())
    
    class Meta:
        model = Module
        fields = ["id", "course", "title", "description", "order", "logro_unidad"]

class LessonSerializer(serializers.ModelSerializer):
    module = serializers.PrimaryKeyRelatedField(queryset=Module.objects.all(), allow_null=True, required=False)
    
    class Meta:
        model = Lesson
        fields = [
            "id", "module", "title", "lesson_type", "order", "is_free", "duration_minutes",
            "content", "structured_content", "video_url", "quiz_questions",
            "logro_semana", "saberes_esenciales", "actividades", "trabajo_campo",
            "created_at", "updated_at",
        ]

class EvaluationSerializer(serializers.ModelSerializer):
    course = serializers.PrimaryKeyRelatedField(queryset=Course.objects.all())
    
    class Meta:
        model = Evaluation
        fields = ["id", "course", "nombre", "peso", "semana", "descripcion", "created_at", "updated_at"]

class BibliografiaSerializer(serializers.ModelSerializer):
    course = serializers.PrimaryKeyRelatedField(queryset=Course.objects.all())
    
    class Meta:
        model = Bibliografia
        fields = ["id", "course", "autor", "titulo", "anio", "enlace", "created_at"]
