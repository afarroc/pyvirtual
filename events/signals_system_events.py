"""
System Events signals for Management360.

Registra automáticamente SystemEvent para acciones relevantes del sistema:
- Task: created, updated, deleted, status changed
- Project: created, updated, deleted, status changed
- InboxItem: created, processed, deleted
- TaskSchedule: created, deleted
- Reminder: created, deleted
- ProjectTemplate: created, used
- Event: created, updated, deleted
"""

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType

from .models import (
    Task, Project, InboxItem, TaskSchedule, Reminder,
    ProjectTemplate, TemplateTask, TaskDependency, Event, SystemEvent
)

User = get_user_model()


def _build_metadata(instance, extra=None):
    meta = {}
    try:
        meta['id'] = instance.pk
        meta['title'] = getattr(instance, 'title', None) or getattr(instance, 'name', None) or str(instance)
        meta['model'] = instance.__class__.__name__
    except Exception:
        pass
    if extra:
        meta.update(extra)
    return meta or None


def _log_system_event(action_type, instance, user=None, metadata=None, summary=None):
    try:
        ct = ContentType.objects.get_for_model(instance)
        SystemEvent.objects.create(
            action_type=action_type,
            user=user,
            content_type=ct,
            object_id=instance.pk,
            metadata=_build_metadata(instance, metadata),
            summary=summary or f"{action_type}: {getattr(instance, 'title', None) or instance.pk}",
        )
    except Exception as exc:
        # Evitar que una falla en auditoría rompa el flujo principal
        print(f"[system_events] Error creando SystemEvent: {exc}")


# ============================================================================
# TASKS
# ============================================================================

@receiver(post_save, sender=Task)
def task_post_save(sender, instance, created, **kwargs):
    user = getattr(instance, 'host', None) or (getattr(instance, 'assigned_to', None) if not created else None)
    if created:
        _log_system_event(
            SystemEvent.ACTION_TASK_CREATED,
            instance,
            user=user,
            summary=f"Task created: {instance.title}",
        )
    else:
        _log_system_event(
            SystemEvent.ACTION_TASK_UPDATED,
            instance,
            user=user,
            summary=f"Task updated: {instance.title}",
        )


@receiver(pre_delete, sender=Task)
def task_pre_delete(sender, instance, **kwargs):
    user = getattr(instance, 'host', None)
    _log_system_event(
        SystemEvent.ACTION_TASK_DELETED,
        instance,
        user=user,
        summary=f"Task deleted: {instance.title}",
    )


@receiver(post_save, sender=Task)
def task_status_changed(sender, instance, created, **kwargs):
    if created:
        return
    # Detectar cambio real de estado si viene seteado desde la view
    if hasattr(instance, '_task_status_changed') and instance._task_status_changed:
        user = getattr(instance, '_task_status_changed_user', None) or getattr(instance, 'host', None)
        _log_system_event(
            SystemEvent.ACTION_TASK_STATUS_CHANGED,
            instance,
            user=user,
            metadata={'new_status': str(instance.task_status) if instance.task_status_id else None},
            summary=f"Task status changed: {instance.title}",
        )


# ============================================================================
# PROJECTS
# ============================================================================

@receiver(post_save, sender=Project)
def project_post_save(sender, instance, created, **kwargs):
    user = getattr(instance, 'host', None) or getattr(instance, 'assigned_to', None)
    if created:
        _log_system_event(
            SystemEvent.ACTION_PROJECT_CREATED,
            instance,
            user=user,
            summary=f"Project created: {instance.title}",
        )
    else:
        _log_system_event(
            SystemEvent.ACTION_PROJECT_UPDATED,
            instance,
            user=user,
            summary=f"Project updated: {instance.title}",
        )


@receiver(pre_delete, sender=Project)
def project_pre_delete(sender, instance, **kwargs):
    user = getattr(instance, 'host', None)
    _log_system_event(
        SystemEvent.ACTION_PROJECT_DELETED,
        instance,
        user=user,
        summary=f"Project deleted: {instance.title}",
    )


# ============================================================================
# INBOX ITEMS
# ============================================================================

@receiver(post_save, sender=InboxItem)
def inbox_post_save(sender, instance, created, **kwargs):
    user = getattr(instance, 'created_by', None)
    if created:
        _log_system_event(
            SystemEvent.ACTION_INBOX_CREATED,
            instance,
            user=user,
            summary=f"Inbox created: {instance.title}",
        )
    else:
        if getattr(instance, 'is_processed', False) and not getattr(instance, '_was_processed', False):
            instance._was_processed = True
            _log_system_event(
                SystemEvent.ACTION_INBOX_PROCESSED,
                instance,
                user=user,
                summary=f"Inbox processed: {instance.title}",
            )


@receiver(pre_delete, sender=InboxItem)
def inbox_pre_delete(sender, instance, **kwargs):
    user = getattr(instance, 'created_by', None)
    _log_system_event(
        SystemEvent.ACTION_INBOX_DELETED,
        instance,
        user=user,
        summary=f"Inbox deleted: {instance.title}",
    )


# ============================================================================
# TASK SCHEDULES
# ============================================================================

@receiver(post_save, sender=TaskSchedule)
def task_schedule_post_save(sender, instance, created, **kwargs):
    if not created:
        return
    user = getattr(instance, 'host', None)
    _log_system_event(
        SystemEvent.ACTION_SCHEDULE_CREATED,
        instance,
        user=user,
        summary=f"Schedule created: {instance.task.title}",
    )


@receiver(pre_delete, sender=TaskSchedule)
def task_schedule_pre_delete(sender, instance, **kwargs):
    user = getattr(instance, 'host', None)
    _log_system_event(
        SystemEvent.ACTION_SCHEDULE_DELETED,
        instance,
        user=user,
        summary=f"Schedule deleted: {instance.task.title}",
    )


# ============================================================================
# REMINDERS
# ============================================================================

@receiver(post_save, sender=Reminder)
def reminder_post_save(sender, instance, created, **kwargs):
    if not created:
        return
    user = getattr(instance, 'created_by', None)
    _log_system_event(
        SystemEvent.ACTION_REMINDER_CREATED,
        instance,
        user=user,
        summary=f"Reminder created: {instance.title}",
    )


@receiver(pre_delete, sender=Reminder)
def reminder_pre_delete(sender, instance, **kwargs):
    user = getattr(instance, 'created_by', None)
    _log_system_event(
        SystemEvent.ACTION_REMINDER_DELETED,
        instance,
        user=user,
        summary=f"Reminder deleted: {instance.title}",
    )


# ============================================================================
# TASK DEPENDENCIES
# ============================================================================

@receiver(post_save, sender=TaskDependency)
def task_dependency_post_save(sender, instance, created, **kwargs):
    if not created:
        return
    user = getattr(instance.task, 'host', None) or getattr(instance.task, 'assigned_to', None)
    _log_system_event(
        SystemEvent.ACTION_OTHER,
        instance,
        user=user,
        summary=f"Task dependency created: {instance.task.title} -> {instance.depends_on.title}",
    )


@receiver(pre_delete, sender=TaskDependency)
def task_dependency_pre_delete(sender, instance, **kwargs):
    user = getattr(instance.task, 'host', None) or getattr(instance.task, 'assigned_to', None)
    _log_system_event(
        SystemEvent.ACTION_OTHER,
        instance,
        user=user,
        summary=f"Task dependency deleted: {instance.task.title} -> {instance.depends_on.title}",
    )


# ============================================================================
# PROJECT TEMPLATES
# ============================================================================

@receiver(post_save, sender=ProjectTemplate)
def project_template_post_save(sender, instance, created, **kwargs):
    user = getattr(instance, 'created_by', None) or getattr(instance, 'host', None)
    _log_system_event(
        SystemEvent.ACTION_TEMPLATE_CREATED,
        instance,
        user=user,
        summary=f"Project template created: {getattr(instance, 'name', instance.pk)}",
    )


@receiver(post_save, sender=TemplateTask)
def template_task_post_save(sender, instance, created, **kwargs):
    if not created:
        return
    user = getattr(instance.template, 'created_by', None) or getattr(instance.template, 'host', None)
    _log_system_event(
        SystemEvent.ACTION_TEMPLATE_USED,
        instance.template,
        user=user,
        metadata={'template_task_id': instance.pk, 'task_title': instance.title},
        summary=f"Project template used: {getattr(instance.template, 'name', instance.template.pk)}",
    )


# ============================================================================
# CALENDAR EVENTS (modelo `Event`)
# Nota: este modelo representa eventos de calendario/reunión, no eventos del sistema.
# El registro de su creación/edición/borrado queda capturado aquí como SystemEvent.
# ============================================================================

@receiver(post_save, sender=Event)
def event_post_save(sender, instance, created, **kwargs):
    user = getattr(instance, 'host', None) or getattr(instance, 'assigned_to', None)
    if created:
        _log_system_event(
            SystemEvent.ACTION_EVENT_CREATED,
            instance,
            user=user,
            summary=f"Event created: {instance.title}",
        )
    else:
        _log_system_event(
            SystemEvent.ACTION_EVENT_UPDATED,
            instance,
            user=user,
            summary=f"Event updated: {instance.title}",
        )


@receiver(pre_delete, sender=Event)
def event_pre_delete(sender, instance, **kwargs):
    user = getattr(instance, 'host', None)
    _log_system_event(
        SystemEvent.ACTION_EVENT_DELETED,
        instance,
        user=user,
        summary=f"Event deleted: {instance.title}",
    )
