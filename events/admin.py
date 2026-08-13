import logging
from decimal import Decimal
from django.contrib import admin
from django.utils import timezone
from django.db.models import Count, Q
from django.urls import reverse
from django.utils.html import format_html
from django.contrib import messages
from .models import (
    # Base models
    Status, ProjectStatus, TaskStatus, Classification,
    
    # Project models
    Project, ProjectState, ProjectHistory, ProjectAttendee,
    
    # Task models
    Task, TaskState, TaskHistory, TaskProgram, TaskSchedule, TaskDependency,
    
    # Event models
    Event, EventState, EventHistory, EventAttendee,
    
    # Tag system
    Tag, TagCategory,
    
    # Template system
    ProjectTemplate, TemplateTask,
    
    # GTD system
    InboxItem, InboxItemAuthorization, InboxItemClassification, 
    InboxItemHistory, GTDClassificationPattern, GTDLearningEntry, 
    GTDProcessingSettings,
    
    # Utility models
    CreditAccount, Reminder, SystemEvent
)

# Configure logger
logger = logging.getLogger(__name__)


# ============================================================================
# BASE ADMIN MIXINS
# ============================================================================

class BaseStatusAdmin(admin.ModelAdmin):
    """Base admin for status models with common configuration"""
    list_display = ('status_name', 'active', 'color', 'icon')
    list_filter = ('active',)
    search_fields = ('status_name',)
    list_editable = ('active', 'color')
    list_per_page = 25


class BaseHistoryAdmin(admin.ModelAdmin):
    """Base admin for history models with common configuration"""
    list_display = ('get_related_object', 'editor', 'field_name', 'edited_at', 'get_value_preview')
    list_filter = ('field_name', 'edited_at', 'editor')
    search_fields = ('editor__username', 'field_name')
    date_hierarchy = 'edited_at'
    readonly_fields = ('edited_at', 'editor', 'field_name', 'old_value', 'new_value')
    list_per_page = 50

    def get_related_object(self, obj):
        """Get the related object with a link if possible"""
        if hasattr(obj, 'project'):
            return format_html('<a href="{}">{}</a>', 
                             reverse('admin:events_project_change', args=[obj.project.id]),
                             obj.project.title)
        elif hasattr(obj, 'task'):
            return format_html('<a href="{}">{}</a>',
                             reverse('admin:events_task_change', args=[obj.task.id]),
                             obj.task.title)
        elif hasattr(obj, 'event'):
            return format_html('<a href="{}">{}</a>',
                             reverse('admin:events_event_change', args=[obj.event.id]),
                             obj.event.title)
        return "N/A"
    get_related_object.short_description = 'Related Object'

    def get_value_preview(self, obj):
        """Get truncated preview of values"""
        old = obj.old_value[:50] + '...' if obj.old_value and len(obj.old_value) > 50 else obj.old_value
        new = obj.new_value[:50] + '...' if obj.new_value and len(obj.new_value) > 50 else obj.new_value
        return f"Old: {old} → New: {new}"
    get_value_preview.short_description = 'Changes'

    def has_add_permission(self, request):
        """Prevent manual addition of history entries"""
        return False

    def has_change_permission(self, request, obj=None):
        """Prevent changes to history entries"""
        return False

    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of history entries"""
        return False


class BaseAttendeeAdmin(admin.ModelAdmin):
    """Base admin for attendee models with common configuration"""
    list_display = ('user', 'get_related_event', 'registration_time', 'has_paid', 'notes_preview')
    list_filter = ('has_paid', 'registration_time')
    search_fields = ('user__username', 'notes')
    date_hierarchy = 'registration_time'
    list_per_page = 25
    actions = ['mark_paid', 'mark_unpaid']

    def get_related_event(self, obj):
        """Get the related event/project with a link"""
        if hasattr(obj, 'event'):
            return format_html('<a href="{}">{}</a>',
                             reverse('admin:events_event_change', args=[obj.event.id]),
                             obj.event.title)
        elif hasattr(obj, 'project'):
            return format_html('<a href="{}">{}</a>',
                             reverse('admin:events_project_change', args=[obj.project.id]),
                             obj.project.title)
        return "N/A"
    get_related_event.short_description = 'Event/Project'

    def notes_preview(self, obj):
        """Get truncated notes preview"""
        return obj.notes[:50] + '...' if obj.notes and len(obj.notes) > 50 else obj.notes
    notes_preview.short_description = 'Notes'

    def mark_paid(self, request, queryset):
        """Mark selected attendees as paid"""
        updated = queryset.update(has_paid=True)
        self.message_user(request, f'{updated} attendees marked as paid.')
        logger.info(f"User {request.user} marked {updated} attendees as paid")
    mark_paid.short_description = 'Mark as paid'

    def mark_unpaid(self, request, queryset):
        """Mark selected attendees as unpaid"""
        updated = queryset.update(has_paid=False)
        self.message_user(request, f'{updated} attendees marked as unpaid.')
        logger.info(f"User {request.user} marked {updated} attendees as unpaid")
    mark_unpaid.short_description = 'Mark as unpaid'


# ============================================================================
# BASE MODEL ADMINS
# ============================================================================

@admin.register(Status)
class StatusAdmin(BaseStatusAdmin):
    """Admin for base Status model"""
    pass


@admin.register(ProjectStatus)
class ProjectStatusAdmin(BaseStatusAdmin):
    """Admin for ProjectStatus model"""
    pass


@admin.register(TaskStatus)
class TaskStatusAdmin(BaseStatusAdmin):
    """Admin for TaskStatus model"""
    pass


@admin.register(Classification)
class ClassificationAdmin(admin.ModelAdmin):
    """Admin for Classification model"""
    list_display = ('nombre', 'descripcion')
    search_fields = ('nombre', 'descripcion')
    list_per_page = 25


# ============================================================================
# TAG SYSTEM ADMINS
# ============================================================================

@admin.register(TagCategory)
class TagCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'color_preview', 'is_system', 'tags_count', 'color')
    list_filter = ('is_system',)
    search_fields = ('name', 'description')
    list_editable = ('color',)  # color must be in list_display
    list_per_page = 25
    
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'color', 'icon', 'is_system')
        }),
    )

    def color_preview(self, obj):
        """Show color preview"""
        return format_html(
            '<span style="background-color: {}; padding: 3px 10px; border-radius: 3px;">{}</span>',
            obj.color, obj.color
        )
    color_preview.short_description = 'Color'

    def tags_count(self, obj):
        """Get count of tags in category"""
        return obj.tag_set.count()
    tags_count.short_description = 'Tags Count'


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'color_preview', 'is_system', 'created_at', 'usage_count', 'color')
    list_filter = ('category', 'is_system', 'created_at')
    search_fields = ('name', 'description')
    list_editable = ('color',)  # color must be in list_display
    date_hierarchy = 'created_at'
    list_per_page = 25
    list_select_related = ('category',)

    def color_preview(self, obj):
        """Show color preview"""
        return format_html(
            '<span style="background-color: {}; padding: 3px 10px; border-radius: 3px;">{}</span>',
            obj.color, obj.color
        )
    color_preview.short_description = 'Color'

    def usage_count(self, obj):
        """Get count of items using this tag"""
        from django.contrib.contenttypes.models import ContentType
        count = 0
        # Count in Tasks
        count += obj.task_set.count()
        # Count in Events
        count += obj.event_set.count()
        # Count in InboxItems
        count += obj.inboxitem_set.count()
        # Count in TemplateTasks
        count += obj.templatetask_set.count()
        return count
    usage_count.short_description = 'Usage Count'


# ============================================================================
# HISTORY STATE ADMINS
# ============================================================================

@admin.register(ProjectState)
class ProjectStateAdmin(admin.ModelAdmin):
    list_display = ('project_link', 'status', 'start_time', 'end_time', 'duration')
    list_filter = ('status', 'start_time')
    search_fields = ('project__title',)
    date_hierarchy = 'start_time'
    readonly_fields = ('start_time', 'end_time')
    list_per_page = 25
    list_select_related = ('project', 'status')

    def project_link(self, obj):
        """Link to the project"""
        return format_html('<a href="{}">{}</a>',
                         reverse('admin:events_project_change', args=[obj.project.id]),
                         obj.project.title)
    project_link.short_description = 'Project'
    project_link.admin_order_field = 'project__title'

    def duration(self, obj):
        """Calculate duration"""
        if obj.start_time and obj.end_time:
            duration = obj.end_time - obj.start_time
            hours = duration.total_seconds() / 3600
            return f"{hours:.1f} hours"
        return "In Progress"
    duration.short_description = 'Duration'


@admin.register(TaskState)
class TaskStateAdmin(admin.ModelAdmin):
    list_display = ('task_link', 'status', 'start_time', 'end_time', 'duration')
    list_filter = ('status', 'start_time')
    search_fields = ('task__title',)
    date_hierarchy = 'start_time'
    readonly_fields = ('start_time', 'end_time')
    list_per_page = 25
    list_select_related = ('task', 'status')

    def task_link(self, obj):
        """Link to the task"""
        return format_html('<a href="{}">{}</a>',
                         reverse('admin:events_task_change', args=[obj.task.id]),
                         obj.task.title)
    task_link.short_description = 'Task'
    task_link.admin_order_field = 'task__title'

    def duration(self, obj):
        """Calculate duration"""
        if obj.start_time and obj.end_time:
            duration = obj.end_time - obj.start_time
            hours = duration.total_seconds() / 3600
            return f"{hours:.1f} hours"
        return "In Progress"
    duration.short_description = 'Duration'


@admin.register(EventState)
class EventStateAdmin(admin.ModelAdmin):
    list_display = ('event_link', 'status', 'start_time', 'end_time', 'duration')
    list_filter = ('status', 'start_time')
    search_fields = ('event__title',)
    date_hierarchy = 'start_time'
    readonly_fields = ('start_time', 'end_time')
    list_per_page = 25
    list_select_related = ('event', 'status')

    def event_link(self, obj):
        """Link to the event"""
        return format_html('<a href="{}">{}</a>',
                         reverse('admin:events_event_change', args=[obj.event.id]),
                         obj.event.title)
    event_link.short_description = 'Event'
    event_link.admin_order_field = 'event__title'

    def duration(self, obj):
        """Calculate duration"""
        if obj.start_time and obj.end_time:
            duration = obj.end_time - obj.start_time
            hours = duration.total_seconds() / 3600
            return f"{hours:.1f} hours"
        return "In Progress"
    duration.short_description = 'Duration'


# ============================================================================
# HISTORY ADMINS
# ============================================================================

@admin.register(ProjectHistory)
class ProjectHistoryAdmin(BaseHistoryAdmin):
    """Admin for ProjectHistory"""
    list_display = ('project_link', 'editor', 'field_name', 'edited_at', 'get_value_preview')
    
    def project_link(self, obj):
        """Link to the project"""
        return format_html('<a href="{}">{}</a>',
                         reverse('admin:events_project_change', args=[obj.project.id]),
                         obj.project.title)
    project_link.short_description = 'Project'


@admin.register(TaskHistory)
class TaskHistoryAdmin(BaseHistoryAdmin):
    """Admin for TaskHistory"""
    list_display = ('task_link', 'editor', 'field_name', 'edited_at', 'get_value_preview')
    
    def task_link(self, obj):
        """Link to the task"""
        return format_html('<a href="{}">{}</a>',
                         reverse('admin:events_task_change', args=[obj.task.id]),
                         obj.task.title)
    task_link.short_description = 'Task'


@admin.register(EventHistory)
class EventHistoryAdmin(BaseHistoryAdmin):
    """Admin for EventHistory"""
    list_display = ('event_link', 'editor', 'field_name', 'edited_at', 'get_value_preview')
    
    def event_link(self, obj):
        """Link to the event"""
        return format_html('<a href="{}">{}</a>',
                         reverse('admin:events_event_change', args=[obj.event.id]),
                         obj.event.title)
    event_link.short_description = 'Event'


# ============================================================================
# PROJECT ADMINS
# ============================================================================

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'host_link', 'project_status', 'event_link', 'created_at', 
                   'updated_at', 'attendees_count', 'status_badge')
    list_filter = ('project_status', 'created_at', 'updated_at', 'event', 'done')
    search_fields = ('title', 'description', 'host__username', 'assigned_to__username')
    list_editable = ('project_status',)
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at', 'attendees_count_display')
    list_per_page = 25
    list_select_related = ('host', 'assigned_to', 'event', 'project_status')
    # Remove filter_horizontal for attendees as it uses a through model
    # filter_horizontal = ('attendees',)  # REMOVED - causes error
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'host', 'assigned_to', 'project_status')
        }),
        ('Event', {
            'fields': ('event', 'done')
        }),
        ('Attendees & Pricing', {
            'fields': ('ticket_price', 'attendees_count_display')  # Removed 'attendees' from here
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def host_link(self, obj):
        """Link to the host user"""
        return format_html('<a href="{}">{}</a>',
                         reverse('admin:accounts_user_change', args=[obj.host.id]),
                         obj.host.username)
    host_link.short_description = 'Host'
    host_link.admin_order_field = 'host__username'

    def event_link(self, obj):
        """Link to the event if exists"""
        if obj.event:
            return format_html('<a href="{}">{}</a>',
                             reverse('admin:events_event_change', args=[obj.event.id]),
                             obj.event.title)
        return "-"
    event_link.short_description = 'Event'

    def attendees_count(self, obj):
        """Get count of attendees"""
        return obj.attendees.count()
    attendees_count.short_description = 'Attendees'

    def attendees_count_display(self, obj):
        """Display attendees count in readonly field"""
        return obj.attendees.count()
    attendees_count_display.short_description = 'Attendees Count'

    def status_badge(self, obj):
        """Show status as colored badge"""
        color_map = {
            'Completed': 'green',
            'In Progress': 'orange',
            'Pending': 'gray',
        }
        color = color_map.get(obj.project_status.status_name, 'blue')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, obj.project_status.status_name
        )
    status_badge.short_description = 'Status'

    actions = ['mark_completed', 'mark_in_progress', 'duplicate_project']

    def mark_completed(self, request, queryset):
        """Mark selected projects as completed"""
        updated = 0
        try:
            completed_status = ProjectStatus.objects.get(status_name='Completed')
            for project in queryset:
                if project.project_status != completed_status:
                    project.change_status(completed_status.id)
                    updated += 1
            self.message_user(request, f'{updated} projects marked as completed.')
            logger.info(f"User {request.user} marked {updated} projects as completed")
        except Exception as e:
            logger.error(f"Error in mark_completed action: {e}")
            self.message_user(request, f'Error: {e}', level='ERROR')
    mark_completed.short_description = 'Mark selected as completed'

    def mark_in_progress(self, request, queryset):
        """Mark selected projects as in progress"""
        updated = 0
        try:
            in_progress_status = ProjectStatus.objects.get(status_name='In Progress')
            for project in queryset:
                if project.project_status != in_progress_status:
                    project.change_status(in_progress_status.id)
                    updated += 1
            self.message_user(request, f'{updated} projects marked as in progress.')
            logger.info(f"User {request.user} marked {updated} projects as in progress")
        except Exception as e:
            logger.error(f"Error in mark_in_progress action: {e}")
            self.message_user(request, f'Error: {e}', level='ERROR')
    mark_in_progress.short_description = 'Mark selected as in progress'

    def duplicate_project(self, request, queryset):
        """Duplicate selected projects"""
        duplicated = 0
        for project in queryset:
            try:
                # Create a copy
                project.pk = None
                project.title = f"{project.title} (Copy)"
                project.created_at = timezone.now()
                project.updated_at = timezone.now()
                project.save()
                duplicated += 1
            except Exception as e:
                logger.error(f"Error duplicating project {project.id}: {e}")
        self.message_user(request, f'{duplicated} projects duplicated.')
        logger.info(f"User {request.user} duplicated {duplicated} projects")
    duplicate_project.short_description = 'Duplicate selected projects'


@admin.register(ProjectAttendee)
class ProjectAttendeeAdmin(BaseAttendeeAdmin):
    """Admin for ProjectAttendee"""
    list_display = ('user', 'project_link', 'registration_time', 'has_paid', 'notes_preview')
    
    def project_link(self, obj):
        """Link to the project"""
        return format_html('<a href="{}">{}</a>',
                         reverse('admin:events_project_change', args=[obj.project.id]),
                         obj.project.title)
    project_link.short_description = 'Project'


# ============================================================================
# TASK ADMINS
# ============================================================================

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'project_link', 'task_status', 'assigned_to_link', 
                   'important', 'created_at', 'status_badge')
    list_filter = ('task_status', 'project', 'important', 'created_at', 'updated_at', 'tags')
    search_fields = ('title', 'description', 'assigned_to__username', 'host__username')
    list_editable = ('task_status', 'important')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at', 'dependencies_count')
    list_per_page = 25
    list_select_related = ('project', 'event', 'task_status', 'assigned_to', 'host')
    filter_horizontal = ('tags',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'host', 'assigned_to', 'task_status')
        }),
        ('Relationships', {
            'fields': ('project', 'event', 'tags')
        }),
        ('Properties', {
            'fields': ('important', 'done', 'ticket_price')
        }),
        ('Statistics', {
            'fields': ('dependencies_count',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def project_link(self, obj):
        """Link to the project if exists"""
        if obj.project:
            return format_html('<a href="{}">{}</a>',
                             reverse('admin:events_project_change', args=[obj.project.id]),
                             obj.project.title)
        return "-"
    project_link.short_description = 'Project'

    def assigned_to_link(self, obj):
        """Link to the assigned user"""
        return format_html('<a href="{}">{}</a>',
                         reverse('admin:accounts_user_change', args=[obj.assigned_to.id]),
                         obj.assigned_to.username)
    assigned_to_link.short_description = 'Assigned To'
    assigned_to_link.admin_order_field = 'assigned_to__username'

    def status_badge(self, obj):
        """Show status as colored badge"""
        color_map = {
            'Completed': 'green',
            'In Progress': 'orange',
            'Pending': 'gray',
            'Blocked': 'red',
        }
        color = color_map.get(obj.task_status.status_name, 'blue')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, obj.task_status.status_name
        )
    status_badge.short_description = 'Status'

    def dependencies_count(self, obj):
        """Get count of dependencies"""
        return obj.dependencies.count()
    dependencies_count.short_description = 'Dependencies Count'

    def get_queryset(self, request):
        """Optimize queryset with counts"""
        return super().get_queryset(request).annotate(
            deps_count=Count('dependencies', distinct=True)
        )

    actions = ['mark_completed', 'mark_in_progress', 'mark_important', 'mark_not_important']

    def mark_completed(self, request, queryset):
        """Mark selected tasks as completed"""
        updated = 0
        try:
            completed_status = TaskStatus.objects.get(status_name='Completed')
            for task in queryset:
                if task.task_status != completed_status:
                    task.change_status(completed_status.id, request.user)
                    updated += 1
            self.message_user(request, f'{updated} tasks marked as completed.')
            logger.info(f"User {request.user} marked {updated} tasks as completed")
        except Exception as e:
            logger.error(f"Error in mark_completed action: {e}")
            self.message_user(request, f'Error: {e}', level='ERROR')
    mark_completed.short_description = 'Mark selected as completed'

    def mark_in_progress(self, request, queryset):
        """Mark selected tasks as in progress"""
        updated = 0
        try:
            in_progress_status = TaskStatus.objects.get(status_name='In Progress')
            for task in queryset:
                if task.task_status != in_progress_status:
                    task.change_status(in_progress_status.id, request.user)
                    updated += 1
            self.message_user(request, f'{updated} tasks marked as in progress.')
            logger.info(f"User {request.user} marked {updated} tasks as in progress")
        except Exception as e:
            logger.error(f"Error in mark_in_progress action: {e}")
            self.message_user(request, f'Error: {e}', level='ERROR')
    mark_in_progress.short_description = 'Mark selected as in progress'

    def mark_important(self, request, queryset):
        """Mark selected tasks as important"""
        updated = queryset.update(important=True)
        self.message_user(request, f'{updated} tasks marked as important.')
        logger.info(f"User {request.user} marked {updated} tasks as important")
    mark_important.short_description = 'Mark as important'

    def mark_not_important(self, request, queryset):
        """Mark selected tasks as not important"""
        updated = queryset.update(important=False)
        self.message_user(request, f'{updated} tasks marked as not important.')
        logger.info(f"User {request.user} marked {updated} tasks as not important")
    mark_not_important.short_description = 'Mark as not important'


@admin.register(TaskProgram)
class TaskProgramAdmin(admin.ModelAdmin):
    list_display = ('title', 'task_link', 'start_time', 'end_time', 'host_link', 
                   'get_duration', 'task_status_badge', 'is_active')
    list_filter = ('start_time', 'end_time', 'host', 'task__task_status')
    search_fields = ('title', 'task__title', 'host__username')
    date_hierarchy = 'start_time'
    readonly_fields = ('created_at', 'get_duration')
    list_per_page = 25
    list_select_related = ('task', 'host', 'task__task_status')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'task', 'host')
        }),
        ('Schedule', {
            'fields': ('start_time', 'end_time', 'get_duration')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def task_link(self, obj):
        """Link to the task"""
        return format_html('<a href="{}">{}</a>',
                         reverse('admin:events_task_change', args=[obj.task.id]),
                         obj.task.title)
    task_link.short_description = 'Task'
    task_link.admin_order_field = 'task__title'

    def host_link(self, obj):
        """Link to the host user"""
        return format_html('<a href="{}">{}</a>',
                         reverse('admin:accounts_user_change', args=[obj.host.id]),
                         obj.host.username)
    host_link.short_description = 'Host'
    host_link.admin_order_field = 'host__username'

    def get_duration(self, obj):
        """Calculate and display program duration"""
        if obj.start_time and obj.end_time:
            duration = obj.end_time - obj.start_time
            hours = duration.total_seconds() / 3600
            minutes = (duration.total_seconds() % 3600) / 60
            return f"{int(hours)}h {int(minutes)}m"
        return "N/A"
    get_duration.short_description = 'Duration'

    def task_status_badge(self, obj):
        """Show task status as colored badge"""
        color_map = {
            'Completed': 'green',
            'In Progress': 'orange',
            'Pending': 'gray',
            'Blocked': 'red',
        }
        color = color_map.get(obj.task.task_status.status_name, 'blue')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, obj.task.task_status.status_name
        )
    task_status_badge.short_description = 'Task Status'
    task_status_badge.admin_order_field = 'task__task_status'

    def is_active(self, obj):
        """Check if program is still active"""
        return obj.end_time > timezone.now() if obj.end_time else False
    is_active.boolean = True
    is_active.short_description = 'Active?'

    actions = ['mark_completed', 'mark_in_progress']

    def mark_completed(self, request, queryset):
        """Mark associated tasks as completed"""
        updated = 0
        try:
            completed_status = TaskStatus.objects.get(status_name='Completed')
            for program in queryset:
                if program.task.task_status != completed_status:
                    program.task.task_status = completed_status
                    program.task.save()
                    updated += 1
            self.message_user(request, f'{updated} tasks marked as completed.')
            logger.info(f"User {request.user} marked {updated} tasks as completed via TaskProgram")
        except Exception as e:
            logger.error(f"Error in TaskProgram mark_completed: {e}")
            self.message_user(request, f'Error: {e}', level='ERROR')
    mark_completed.short_description = 'Mark associated tasks as completed'

    def mark_in_progress(self, request, queryset):
        """Mark associated tasks as in progress"""
        updated = 0
        try:
            in_progress_status = TaskStatus.objects.get(status_name='In Progress')
            for program in queryset:
                if program.task.task_status != in_progress_status:
                    program.task.task_status = in_progress_status
                    program.task.save()
                    updated += 1
            self.message_user(request, f'{updated} tasks marked as in progress.')
            logger.info(f"User {request.user} marked {updated} tasks as in progress via TaskProgram")
        except Exception as e:
            logger.error(f"Error in TaskProgram mark_in_progress: {e}")
            self.message_user(request, f'Error: {e}', level='ERROR')
    mark_in_progress.short_description = 'Mark associated tasks as in progress'


@admin.register(TaskSchedule)
class TaskScheduleAdmin(admin.ModelAdmin):
    list_display = ('task_link', 'host_link', 'recurrence_type', 'days_display', 
                   'start_time', 'duration', 'is_active', 'is_active_badge', 
                   'next_occurrence', 'programs_count', 'created_at')  # Added is_active to list_display
    list_filter = ('recurrence_type', 'is_active', 'start_date', 'end_date', 'created_at', 'host')
    search_fields = ('task__title', 'host__username')
    list_editable = ('is_active',)  # is_active is now in list_display
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at', 'next_occurrence', 'programs_count')
    list_per_page = 25
    list_select_related = ('task', 'host')

    fieldsets = (
        ('Basic Information', {
            'fields': ('task', 'host', 'is_active')
        }),
        ('Recurrence Configuration', {
            'fields': ('recurrence_type', 'start_time', 'duration', 'start_date', 'end_date')
        }),
        ('Days of Week', {
            'fields': ('monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('next_occurrence', 'programs_count'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def task_link(self, obj):
        """Link to the task"""
        return format_html('<a href="{}">{}</a>',
                         reverse('admin:events_task_change', args=[obj.task.id]),
                         obj.task.title)
    task_link.short_description = 'Task'
    task_link.admin_order_field = 'task__title'

    def host_link(self, obj):
        """Link to the host user"""
        return format_html('<a href="{}">{}</a>',
                         reverse('admin:accounts_user_change', args=[obj.host.id]),
                         obj.host.username)
    host_link.short_description = 'Host'
    host_link.admin_order_field = 'host__username'

    def days_display(self, obj):
        """Display selected days in compact format"""
        days = []
        if obj.monday: days.append('M')
        if obj.tuesday: days.append('T')
        if obj.wednesday: days.append('W')
        if obj.thursday: days.append('T')
        if obj.friday: days.append('F')
        if obj.saturday: days.append('S')
        if obj.sunday: days.append('S')
        return " ".join(days) if days else "None"
    days_display.short_description = 'Days'

    def is_active_badge(self, obj):
        """Show active status as badge"""
        if obj.is_active_schedule():
            return format_html('<span style="color: green;">✓ Active</span>')
        return format_html('<span style="color: gray;">✗ Inactive</span>')
    is_active_badge.short_description = 'Status'

    def next_occurrence(self, obj):
        """Display next occurrence"""
        next_occ = obj.get_next_occurrence()
        if next_occ:
            return f"{next_occ['date']} {next_occ['start_time'].strftime('%H:%M')}"
        return "No future occurrences"
    next_occurrence.short_description = 'Next Occurrence'

    def programs_count(self, obj):
        """Display number of generated programs"""
        from .models import TaskProgram
        return TaskProgram.objects.filter(task=obj.task, host=obj.host).count()
    programs_count.short_description = 'Programs'

    def get_queryset(self, request):
        """Optimize queries with select_related"""
        return super().get_queryset(request).select_related('task', 'host')

    actions = ['activate_schedules', 'deactivate_schedules', 'generate_programs']

    def activate_schedules(self, request, queryset):
        """Activate selected schedules"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} schedules activated successfully.')
        logger.info(f"User {request.user} activated {updated} schedules")
    activate_schedules.short_description = 'Activate selected schedules'

    def deactivate_schedules(self, request, queryset):
        """Deactivate selected schedules"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} schedules deactivated successfully.')
        logger.info(f"User {request.user} deactivated {updated} schedules")
    deactivate_schedules.short_description = 'Deactivate selected schedules'

    def generate_programs(self, request, queryset):
        """Generate programs for selected schedules"""
        total_created = 0
        for schedule in queryset.filter(is_active=True):
            try:
                created_programs = schedule.create_task_programs()
                total_created += len(created_programs)
            except Exception as e:
                logger.error(f"Error generating programs for schedule {schedule.id}: {e}")
        self.message_user(request, f'Generated {total_created} programs for selected schedules.')
        logger.info(f"User {request.user} generated {total_created} programs")
    generate_programs.short_description = 'Generate programs for active schedules'


@admin.register(TaskDependency)
class TaskDependencyAdmin(admin.ModelAdmin):
    list_display = ('task_link', 'depends_on_link', 'dependency_type', 'created_at')
    list_filter = ('dependency_type', 'created_at')
    search_fields = ('task__title', 'depends_on__title')
    date_hierarchy = 'created_at'
    list_per_page = 25
    list_select_related = ('task', 'depends_on')
    
    fieldsets = (
        (None, {
            'fields': ('task', 'depends_on', 'dependency_type')
        }),
    )

    def task_link(self, obj):
        """Link to the task"""
        return format_html('<a href="{}">{}</a>',
                         reverse('admin:events_task_change', args=[obj.task.id]),
                         obj.task.title)
    task_link.short_description = 'Task'

    def depends_on_link(self, obj):
        """Link to the dependency task"""
        return format_html('<a href="{}">{}</a>',
                         reverse('admin:events_task_change', args=[obj.depends_on.id]),
                         obj.depends_on.title)
    depends_on_link.short_description = 'Depends On'


# ============================================================================
# EVENT ADMINS
# ============================================================================

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'host_link', 'event_status', 'venue', 'event_category', 
                   'created_at', 'attendees_count', 'status_badge')
    list_filter = ('event_status', 'event_category', 'created_at', 'updated_at')
    search_fields = ('title', 'description', 'host__username', 'assigned_to__username', 'venue')
    list_editable = ('event_status',)
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at', 'attendees_count_display')
    list_per_page = 25
    list_select_related = ('host', 'assigned_to', 'event_status')
    # Remove filter_horizontal for attendees as it uses a through model
    # filter_horizontal = ('attendees', 'tags', 'links')  # REMOVED - attendees causes error
    filter_horizontal = ('tags', 'links')  # Only tags and links work with filter_horizontal
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'host', 'assigned_to', 'event_status')
        }),
        ('Location & Category', {
            'fields': ('venue', 'event_category', 'classification')
        }),
        ('Attendees & Pricing', {
            'fields': ('max_attendees', 'ticket_price', 'attendees_count_display')  # Removed 'attendees' from here
        }),
        ('Relationships', {
            'fields': ('tags', 'links')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def host_link(self, obj):
        """Link to the host user"""
        return format_html('<a href="{}">{}</a>',
                         reverse('admin:accounts_user_change', args=[obj.host.id]),
                         obj.host.username)
    host_link.short_description = 'Host'
    host_link.admin_order_field = 'host__username'

    def attendees_count(self, obj):
        """Get count of attendees"""
        return obj.attendees.count()
    attendees_count.short_description = 'Attendees'

    def attendees_count_display(self, obj):
        """Display attendees count in readonly field"""
        count = obj.attendees.count()
        max_count = obj.max_attendees or '∞'
        return f"{count} / {max_count}"
    attendees_count_display.short_description = 'Attendees'

    def status_badge(self, obj):
        """Show status as colored badge"""
        color_map = {
            'Completed': 'green',
            'In Progress': 'orange',
            'Pending': 'gray',
            'Cancelled': 'red',
        }
        color = color_map.get(obj.event_status.status_name, 'blue')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, obj.event_status.status_name
        )
    status_badge.short_description = 'Status'

    actions = ['mark_completed', 'mark_in_progress', 'duplicate_event']

    def mark_completed(self, request, queryset):
        """Mark selected events as completed"""
        updated = 0
        try:
            completed_status = Status.objects.get(status_name='Completed')
            for event in queryset:
                if event.event_status != completed_status:
                    event.change_status(completed_status.id)
                    updated += 1
            self.message_user(request, f'{updated} events marked as completed.')
            logger.info(f"User {request.user} marked {updated} events as completed")
        except Exception as e:
            logger.error(f"Error in Event mark_completed: {e}")
            self.message_user(request, f'Error: {e}', level='ERROR')
    mark_completed.short_description = 'Mark selected as completed'

    def mark_in_progress(self, request, queryset):
        """Mark selected events as in progress"""
        updated = 0
        try:
            in_progress_status = Status.objects.get(status_name='In Progress')
            for event in queryset:
                if event.event_status != in_progress_status:
                    event.change_status(in_progress_status.id)
                    updated += 1
            self.message_user(request, f'{updated} events marked as in progress.')
            logger.info(f"User {request.user} marked {updated} events as in progress")
        except Exception as e:
            logger.error(f"Error in Event mark_in_progress: {e}")
            self.message_user(request, f'Error: {e}', level='ERROR')
    mark_in_progress.short_description = 'Mark selected as in progress'

    def duplicate_event(self, request, queryset):
        """Duplicate selected events"""
        duplicated = 0
        for event in queryset:
            try:
                # Create a copy
                event.pk = None
                event.title = f"{event.title} (Copy)"
                event.created_at = timezone.now()
                event.updated_at = timezone.now()
                event.save()
                duplicated += 1
            except Exception as e:
                logger.error(f"Error duplicating event {event.id}: {e}")
        self.message_user(request, f'{duplicated} events duplicated.')
        logger.info(f"User {request.user} duplicated {duplicated} events")
    duplicate_event.short_description = 'Duplicate selected events'


@admin.register(EventAttendee)
class EventAttendeeAdmin(BaseAttendeeAdmin):
    """Admin for EventAttendee"""
    list_display = ('user', 'event_link', 'registration_time', 'has_paid', 'notes_preview')
    
    def event_link(self, obj):
        """Link to the event"""
        return format_html('<a href="{}">{}</a>',
                         reverse('admin:events_event_change', args=[obj.event.id]),
                         obj.event.title)
    event_link.short_description = 'Event'


# ============================================================================
# PROJECT TEMPLATE ADMINS
# ============================================================================

@admin.register(ProjectTemplate)
class ProjectTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'estimated_duration', 'is_public', 'is_public_badge', 
                   'created_by_link', 'created_at', 'tasks_count')  # Added is_public to list_display
    list_filter = ('category', 'is_public', 'created_at')
    search_fields = ('name', 'description', 'category')
    list_editable = ('is_public',)  # is_public is now in list_display
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'tasks_count')
    list_per_page = 25
    list_select_related = ('created_by',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'category', 'estimated_duration')
        }),
        ('Visibility', {
            'fields': ('is_public', 'created_by')
        }),
        ('Statistics', {
            'fields': ('tasks_count',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def is_public_badge(self, obj):
        """Show public status as badge"""
        if obj.is_public:
            return format_html('<span style="color: green;">✓ Public</span>')
        return format_html('<span style="color: gray;">✗ Private</span>')
    is_public_badge.short_description = 'Public'

    def created_by_link(self, obj):
        """Link to the creator user"""
        return format_html('<a href="{}">{}</a>',
                         reverse('admin:accounts_user_change', args=[obj.created_by.id]),
                         obj.created_by.username)
    created_by_link.short_description = 'Created By'

    def tasks_count(self, obj):
        """Get count of tasks in template"""
        return obj.templatetask_set.count()
    tasks_count.short_description = 'Tasks'

    actions = ['make_public', 'make_private', 'duplicate_template']

    def make_public(self, request, queryset):
        """Make templates public"""
        updated = queryset.update(is_public=True)
        self.message_user(request, f'{updated} templates made public.')
        logger.info(f"User {request.user} made {updated} templates public")
    make_public.short_description = 'Make public'

    def make_private(self, request, queryset):
        """Make templates private"""
        updated = queryset.update(is_public=False)
        self.message_user(request, f'{updated} templates made private.')
        logger.info(f"User {request.user} made {updated} templates private")
    make_private.short_description = 'Make private'

    def duplicate_template(self, request, queryset):
        """Duplicate selected templates"""
        duplicated = 0
        for template in queryset:
            try:
                # Create a copy
                template.pk = None
                template.name = f"{template.name} (Copy)"
                template.created_at = timezone.now()
                template.save()
                duplicated += 1
            except Exception as e:
                logger.error(f"Error duplicating template {template.id}: {e}")
        self.message_user(request, f'{duplicated} templates duplicated.')
        logger.info(f"User {request.user} duplicated {duplicated} templates")
    duplicate_template.short_description = 'Duplicate selected templates'


@admin.register(TemplateTask)
class TemplateTaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'template_link', 'order', 'estimated_hours', 'skills_preview')
    list_filter = ('template', 'order')
    search_fields = ('title', 'description', 'template__name')
    list_editable = ('order', 'estimated_hours')
    list_per_page = 25
    list_select_related = ('template',)
    filter_horizontal = ('required_skills',)
    
    fieldsets = (
        (None, {
            'fields': ('template', 'title', 'description', 'order', 'estimated_hours', 'required_skills')
        }),
    )

    def template_link(self, obj):
        """Link to the template"""
        return format_html('<a href="{}">{}</a>',
                         reverse('admin:events_projecttemplate_change', args=[obj.template.id]),
                         obj.template.name)
    template_link.short_description = 'Template'
    template_link.admin_order_field = 'template__name'

    def skills_preview(self, obj):
        """Preview required skills"""
        skills = obj.required_skills.all()[:3]
        if skills:
            return ", ".join([s.name for s in skills])
        return "None"
    skills_preview.short_description = 'Required Skills'


# ============================================================================
# GTD (GETTING THINGS DONE) ADMINS
# ============================================================================

@admin.register(InboxItem)
class InboxItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'gtd_category_badge', 'action_type_badge', 'priority_badge', 
                   'created_by_link', 'assigned_to_link', 'is_processed', 'is_processed_badge', 
                   'is_public', 'created_at', 'tags_preview')
    list_filter = ('is_processed', 'gtd_category', 'action_type', 'priority', 
                  'is_public', 'created_at', 'created_by', 'assigned_to', 
                  'tags', 'energy_required')
    search_fields = ('title', 'description', 'created_by__username', 
                    'assigned_to__username', 'context', 'notes')
    list_editable = ('is_processed',)
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'processed_at', 'last_activity', 'view_count', 
                      'classification_consensus', 'action_type_consensus',
                      'authorizations_link', 'classification_votes_link')
    list_per_page = 25
    list_select_related = ('created_by', 'assigned_to')
    filter_horizontal = ('tags',)
    radio_fields = {'gtd_category': admin.HORIZONTAL, 'priority': admin.HORIZONTAL}

    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'created_by', 'assigned_to', 'is_public')
        }),
        ('GTD Classification', {
            'fields': ('gtd_category', 'action_type', 'priority', 'energy_required', 
                      'context', 'estimated_time', 'due_date')
        }),
        ('Consensus Information', {
            'fields': ('classification_consensus', 'action_type_consensus'),
            'classes': ('collapse',)
        }),
        ('Status & Processing', {
            'fields': ('is_processed', 'processed_to_content_type', 'processed_to_object_id')
        }),
        ('Tags & Metadata', {
            'fields': ('tags', 'notes', 'waiting_for', 'waiting_for_date', 
                      'next_review_date', 'review_notes', 'created_during', 'user_context')
        }),
        ('Related Data', {
            'fields': ('authorizations_link', 'classification_votes_link'),
            'classes': ('collapse',)
        }),
        ('Read-only Fields', {
            'fields': ('created_at', 'processed_at', 'view_count', 'last_activity'),
            'classes': ('collapse',)
        }),
    )

    # Enlaces dinámicos a los admins relacionados
    def authorizations_link(self, obj):
        from django.urls import reverse
        url = reverse('admin:events_inboxitemauthorization_changelist')
        return format_html('<a href="{}">Manage Authorizations</a>', url)
    authorizations_link.short_description = 'Authorizations'

    def classification_votes_link(self, obj):
        from django.urls import reverse
        url = reverse('admin:events_inboxitemclassification_changelist')
        return format_html('<a href="{}">Manage Classification Votes</a>', url)
    classification_votes_link.short_description = 'Classification Votes'

    # Métodos de visualización (badges, enlaces a usuarios, etc.)
    def gtd_category_badge(self, obj):
        colors = {
            'actionable': 'green',
            'non_actionable': 'gray',
            'pending': 'orange',
        }
        color = colors.get(obj.gtd_category, 'blue')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, obj.get_gtd_category_display()
        )
    gtd_category_badge.short_description = 'GTD Category'
    gtd_category_badge.admin_order_field = 'gtd_category'

    def action_type_badge(self, obj):
        if obj.action_type:
            colors = {
                'do': 'green',
                'delegate': 'orange',
                'defer': 'blue',
                'project': 'purple',
                'delete': 'red',
                'archive': 'gray',
                'incubate': 'teal',
                'waiting': 'yellow',
            }
            color = colors.get(obj.action_type, 'gray')
            return format_html(
                '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
                color, obj.get_action_type_display()
            )
        return "-"
    action_type_badge.short_description = 'Action Type'

    def priority_badge(self, obj):
        colors = {
            'high': 'red',
            'medium': 'orange',
            'low': 'green',
        }
        color = colors.get(obj.priority, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, obj.get_priority_display()
        )
    priority_badge.short_description = 'Priority'
    priority_badge.admin_order_field = 'priority'

    def is_processed_badge(self, obj):
        if obj.is_processed:
            return format_html('<span style="color: green;">✓ Processed</span>')
        return format_html('<span style="color: orange;">⟳ Pending</span>')
    is_processed_badge.short_description = 'Processed'

    def created_by_link(self, obj):
        from django.urls import reverse
        return format_html('<a href="{}">{}</a>',
                         reverse('admin:accounts_user_change', args=[obj.created_by.id]),
                         obj.created_by.username)
    created_by_link.short_description = 'Created By'
    created_by_link.admin_order_field = 'created_by__username'

    def assigned_to_link(self, obj):
        from django.urls import reverse
        if obj.assigned_to:
            return format_html('<a href="{}">{}</a>',
                             reverse('admin:accounts_user_change', args=[obj.assigned_to.id]),
                             obj.assigned_to.username)
        return "-"
    assigned_to_link.short_description = 'Assigned To'
    assigned_to_link.admin_order_field = 'assigned_to__username'

    def tags_preview(self, obj):
        tags = obj.tags.all()[:3]
        if tags:
            return ", ".join([t.name for t in tags])
        return "None"
    tags_preview.short_description = 'Tags'

    def classification_consensus(self, obj):
        return obj.get_classification_consensus()
    classification_consensus.short_description = 'Consensus'

    def action_type_consensus(self, obj):
        return obj.get_action_type_consensus()
    action_type_consensus.short_description = 'Action Consensus'

    # Optimización de queryset
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'created_by', 'assigned_to'
        ).prefetch_related('tags')

    # Acciones personalizadas
    actions = ['mark_processed', 'mark_unprocessed', 'assign_to_current_user', 
               'make_public', 'make_private', 'auto_classify', 'apply_consensus']

    def mark_processed(self, request, queryset):
        updated = queryset.update(is_processed=True, processed_at=timezone.now())
        self.message_user(request, f'{updated} items marked as processed.')
        logger.info(f"User {request.user} marked {updated} inbox items as processed")
    mark_processed.short_description = 'Mark as processed'

    def mark_unprocessed(self, request, queryset):
        updated = queryset.update(is_processed=False, processed_at=None)
        self.message_user(request, f'{updated} items marked as unprocessed.')
        logger.info(f"User {request.user} marked {updated} inbox items as unprocessed")
    mark_unprocessed.short_description = 'Mark as unprocessed'

    def assign_to_current_user(self, request, queryset):
        updated = queryset.update(assigned_to=request.user)
        self.message_user(request, f'{updated} items assigned to {request.user.username}.')
        logger.info(f"User {request.user} assigned {updated} inbox items to themselves")
    assign_to_current_user.short_description = 'Assign to me'

    def make_public(self, request, queryset):
        updated = queryset.update(is_public=True)
        self.message_user(request, f'{updated} items made public.')
        logger.info(f"User {request.user} made {updated} inbox items public")
    make_public.short_description = 'Make public'

    def make_private(self, request, queryset):
        updated = queryset.update(is_public=False)
        self.message_user(request, f'{updated} items made private.')
        logger.info(f"User {request.user} made {updated} inbox items private")
    make_private.short_description = 'Make private'

    def auto_classify(self, request, queryset):
        classified = 0
        patterns = GTDClassificationPattern.objects.filter(is_active=True)
        
        for item in queryset.filter(is_processed=False):
            try:
                title_lower = item.title.lower()
                for pattern in patterns:
                    if pattern.keywords_operator == 'OR':
                        if any(kw.lower() in title_lower for kw in pattern.keywords):
                            item.gtd_category = pattern.gtd_category
                            item.action_type = pattern.action_type
                            item.priority = pattern.priority
                            item.energy_required = pattern.energy_required
                            item.save()
                            pattern.usage_count += 1
                            pattern.save()
                            classified += 1
                            break
                    elif pattern.keywords_operator == 'AND':
                        if all(kw.lower() in title_lower for kw in pattern.keywords):
                            item.gtd_category = pattern.gtd_category
                            item.action_type = pattern.action_type
                            item.priority = pattern.priority
                            item.energy_required = pattern.energy_required
                            item.save()
                            pattern.usage_count += 1
                            pattern.save()
                            classified += 1
                            break
            except Exception as e:
                logger.error(f"Error auto-classifying inbox item {item.id}: {e}")
        
        self.message_user(request, f'Classified {classified} items using patterns.')
        logger.info(f"User {request.user} auto-classified {classified} inbox items")
    auto_classify.short_description = 'Auto-classify using patterns'

    def apply_consensus(self, request, queryset):
        updated = 0
        for item in queryset:
            try:
                consensus = item.get_classification_consensus()
                action_consensus = item.get_action_type_consensus()
                
                if consensus != item.gtd_category:
                    item.gtd_category = consensus
                    item.save()
                    updated += 1
                
                if action_consensus and action_consensus != item.action_type:
                    item.action_type = action_consensus
                    item.save()
                    updated += 1
            except Exception as e:
                logger.error(f"Error applying consensus to inbox item {item.id}: {e}")
        
        self.message_user(request, f'Applied consensus to {updated} fields.')
        logger.info(f"User {request.user} applied consensus to {updated} inbox item fields")
    apply_consensus.short_description = 'Apply voting consensus'


@admin.register(InboxItemAuthorization)
class InboxItemAuthorizationAdmin(admin.ModelAdmin):
    list_display = ('inbox_item_link', 'user_link', 'permission_level_badge', 
                   'granted_by_link', 'granted_at')
    list_filter = ('permission_level', 'granted_at', 'granted_by')
    search_fields = ('inbox_item__title', 'user__username', 'granted_by__username')
    date_hierarchy = 'granted_at'
    readonly_fields = ('granted_at',)
    list_per_page = 25
    list_select_related = ('inbox_item', 'user', 'granted_by')
    
    fieldsets = (
        (None, {
            'fields': ('inbox_item', 'user', 'permission_level', 'granted_by')
        }),
    )

    def inbox_item_link(self, obj):
        """Link to inbox item"""
        return format_html('<a href="{}">{}</a>',
                         reverse('admin:events_inboxitem_change', args=[obj.inbox_item.id]),
                         obj.inbox_item.title)
    inbox_item_link.short_description = 'Inbox Item'

    def user_link(self, obj):
        """Link to user"""
        return format_html('<a href="{}">{}</a>',
                         reverse('admin:accounts_user_change', args=[obj.user.id]),
                         obj.user.username)
    user_link.short_description = 'User'

    def granted_by_link(self, obj):
        """Link to grantor"""
        return format_html('<a href="{}">{}</a>',
                         reverse('admin:accounts_user_change', args=[obj.granted_by.id]),
                         obj.granted_by.username)
    granted_by_link.short_description = 'Granted By'

    def permission_level_badge(self, obj):
        """Show permission level as badge"""
        colors = {
            'view': 'gray',
            'classify': 'blue',
            'edit': 'orange',
            'admin': 'red',
        }
        color = colors.get(obj.permission_level, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, obj.get_permission_level_display()
        )
    permission_level_badge.short_description = 'Permission'


@admin.register(InboxItemClassification)
class InboxItemClassificationAdmin(admin.ModelAdmin):
    list_display = ('inbox_item_link', 'user_link', 'gtd_category_badge', 
                   'action_type_badge', 'priority_badge', 'confidence', 
                   'created_at', 'updated_at')
    list_filter = ('gtd_category', 'action_type', 'priority', 'created_at', 'user')
    search_fields = ('inbox_item__title', 'user__username', 'notes')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at')
    list_editable = ('confidence',)
    list_per_page = 25
    list_select_related = ('inbox_item', 'user')
    
    fieldsets = (
        ('Classification', {
            'fields': ('inbox_item', 'user', 'gtd_category', 'action_type', 
                      'priority', 'confidence', 'notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def inbox_item_link(self, obj):
        """Link to inbox item"""
        return format_html('<a href="{}">{}</a>',
                         reverse('admin:events_inboxitem_change', args=[obj.inbox_item.id]),
                         obj.inbox_item.title)
    inbox_item_link.short_description = 'Inbox Item'

    def user_link(self, obj):
        """Link to user"""
        return format_html('<a href="{}">{}</a>',
                         reverse('admin:accounts_user_change', args=[obj.user.id]),
                         obj.user.username)
    user_link.short_description = 'User'

    def gtd_category_badge(self, obj):
        """Show GTD category as badge"""
        colors = {
            'actionable': 'green',
            'non_actionable': 'gray',
            'pending': 'orange',
        }
        color = colors.get(obj.gtd_category, 'blue')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, obj.get_gtd_category_display()
        )
    gtd_category_badge.short_description = 'GTD Category'

    def action_type_badge(self, obj):
        """Show action type as badge"""
        if obj.action_type:
            colors = {
                'do': 'green',
                'delegate': 'orange',
                'defer': 'blue',
                'project': 'purple',
                'delete': 'red',
                'archive': 'gray',
                'incubate': 'teal',
                'waiting': 'yellow',
            }
            color = colors.get(obj.action_type, 'gray')
            return format_html(
                '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
                color, obj.get_action_type_display()
            )
        return "-"
    action_type_badge.short_description = 'Action Type'

    def priority_badge(self, obj):
        """Show priority as badge"""
        colors = {
            'high': 'red',
            'medium': 'orange',
            'low': 'green',
        }
        color = colors.get(obj.priority, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, obj.get_priority_display()
        )
    priority_badge.short_description = 'Priority'


@admin.register(InboxItemHistory)
class InboxItemHistoryAdmin(admin.ModelAdmin):
    list_display = ('inbox_item_link', 'user_link', 'action_badge', 'timestamp', 'ip_address')
    list_filter = ('action', 'timestamp', 'user')
    search_fields = ('inbox_item__title', 'user__username')
    date_hierarchy = 'timestamp'
    readonly_fields = ('timestamp', 'ip_address', 'user_agent', 'old_values', 'new_values')
    list_per_page = 50
    list_select_related = ('inbox_item', 'user')
    
    fieldsets = (
        ('History Entry', {
            'fields': ('inbox_item', 'user', 'action', 'timestamp')
        }),
        ('Changes', {
            'fields': ('old_values', 'new_values')
        }),
        ('Request Info', {
            'fields': ('ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
    )

    def inbox_item_link(self, obj):
        """Link to inbox item"""
        return format_html('<a href="{}">{}</a>',
                         reverse('admin:events_inboxitem_change', args=[obj.inbox_item.id]),
                         obj.inbox_item.title)
    inbox_item_link.short_description = 'Inbox Item'

    def user_link(self, obj):
        """Link to user"""
        return format_html('<a href="{}">{}</a>',
                         reverse('admin:accounts_user_change', args=[obj.user.id]),
                         obj.user.username)
    user_link.short_description = 'User'

    def action_badge(self, obj):
        """Show action as badge"""
        colors = {
            'created': 'green',
            'viewed': 'gray',
            'classified': 'blue',
            'edited': 'orange',
            'processed': 'purple',
            'shared': 'teal',
            'authorized': 'yellow',
        }
        color = colors.get(obj.action, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, obj.get_action_display()
        )
    action_badge.short_description = 'Action'

    def has_add_permission(self, request):
        """Prevent manual addition of history entries"""
        return False

    def has_change_permission(self, request, obj=None):
        """Prevent changes to history entries"""
        return False

    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of history entries"""
        return False


@admin.register(GTDClassificationPattern)
class GTDClassificationPatternAdmin(admin.ModelAdmin):
    list_display = ('name', 'gtd_category_badge', 'action_type_badge', 'priority_badge', 
                   'keywords_preview', 'is_active', 'is_active_badge', 'usage_count', 
                   'created_by_link', 'created_at')  # Added is_active to list_display
    list_filter = ('gtd_category', 'action_type', 'priority', 'is_active', 'created_at', 'created_by')
    search_fields = ('name', 'description', 'keywords', 'created_by__username')
    list_editable = ('is_active',)  # is_active is now in list_display
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at', 'usage_count')
    list_per_page = 25
    list_select_related = ('created_by',)

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'is_active', 'created_by')
        }),
        ('Pattern Conditions', {
            'fields': ('keywords', 'keywords_operator')
        }),
        ('Classification Results', {
            'fields': ('gtd_category', 'action_type', 'priority', 'energy_required')
        }),
        ('Configuration', {
            'fields': ('confidence_score', 'usage_count')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def gtd_category_badge(self, obj):
        """Show GTD category as badge"""
        colors = {
            'actionable': 'green',
            'non_actionable': 'gray',
            'pending': 'orange',
        }
        color = colors.get(obj.gtd_category, 'blue')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, obj.get_gtd_category_display()
        )
    gtd_category_badge.short_description = 'GTD Category'

    def action_type_badge(self, obj):
        """Show action type as badge"""
        colors = {
            'do': 'green',
            'delegate': 'orange',
            'defer': 'blue',
            'project': 'purple',
            'delete': 'red',
            'archive': 'gray',
            'incubate': 'teal',
            'waiting': 'yellow',
        }
        color = colors.get(obj.action_type, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, obj.get_action_type_display()
        )
    action_type_badge.short_description = 'Action Type'

    def priority_badge(self, obj):
        """Show priority as badge"""
        colors = {
            'high': 'red',
            'medium': 'orange',
            'low': 'green',
        }
        color = colors.get(obj.priority, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, obj.get_priority_display()
        )
    priority_badge.short_description = 'Priority'

    def keywords_preview(self, obj):
        """Preview keywords"""
        if isinstance(obj.keywords, list):
            return ", ".join(obj.keywords[:5])
        return str(obj.keywords)[:50]
    keywords_preview.short_description = 'Keywords'

    def is_active_badge(self, obj):
        """Show active status as badge"""
        if obj.is_active:
            return format_html('<span style="color: green;">✓ Active</span>')
        return format_html('<span style="color: gray;">✗ Inactive</span>')
    is_active_badge.short_description = 'Active'

    def created_by_link(self, obj):
        """Link to creator user"""
        return format_html('<a href="{}">{}</a>',
                         reverse('admin:accounts_user_change', args=[obj.created_by.id]),
                         obj.created_by.username)
    created_by_link.short_description = 'Created By'

    actions = ['activate_patterns', 'deactivate_patterns', 'duplicate_pattern']

    def activate_patterns(self, request, queryset):
        """Activate selected patterns"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} patterns activated.')
        logger.info(f"User {request.user} activated {updated} patterns")
    activate_patterns.short_description = 'Activate selected patterns'

    def deactivate_patterns(self, request, queryset):
        """Deactivate selected patterns"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} patterns deactivated.')
        logger.info(f"User {request.user} deactivated {updated} patterns")
    deactivate_patterns.short_description = 'Deactivate selected patterns'

    def duplicate_pattern(self, request, queryset):
        """Duplicate selected patterns"""
        duplicated = 0
        for pattern in queryset:
            try:
                pattern.pk = None
                pattern.name = f"{pattern.name} (Copy)"
                pattern.usage_count = 0
                pattern.created_at = timezone.now()
                pattern.updated_at = timezone.now()
                pattern.save()
                duplicated += 1
            except Exception as e:
                logger.error(f"Error duplicating pattern {pattern.id}: {e}")
        self.message_user(request, f'{duplicated} patterns duplicated.')
        logger.info(f"User {request.user} duplicated {duplicated} patterns")
    duplicate_pattern.short_description = 'Duplicate selected patterns'


@admin.register(GTDLearningEntry)
class GTDLearningEntryAdmin(admin.ModelAdmin):
    list_display = ('inbox_item_link', 'user_link', 'user_gtd_category_badge', 
                   'user_action_type_badge', 'was_correct_badge', 'prediction_confidence', 
                   'learned_at')
    list_filter = ('user_gtd_category', 'user_action_type', 'was_correct', 'learned_at', 'user')
    search_fields = ('inbox_item__title', 'user__username')
    date_hierarchy = 'learned_at'
    readonly_fields = ('learned_at',)
    list_per_page = 25
    list_select_related = ('inbox_item', 'user')
    
    fieldsets = (
        ('Entry', {
            'fields': ('inbox_item', 'user', 'learned_at')
        }),
        ('User Decision', {
            'fields': ('user_gtd_category', 'user_action_type', 'user_priority')
        }),
        ('System Prediction', {
            'fields': ('predicted_gtd_category', 'predicted_action_type', 
                      'predicted_priority', 'prediction_confidence', 'was_correct')
        }),
    )

    def inbox_item_link(self, obj):
        """Link to inbox item"""
        return format_html('<a href="{}">{}</a>',
                         reverse('admin:events_inboxitem_change', args=[obj.inbox_item.id]),
                         obj.inbox_item.title)
    inbox_item_link.short_description = 'Inbox Item'

    def user_link(self, obj):
        """Link to user"""
        return format_html('<a href="{}">{}</a>',
                         reverse('admin:accounts_user_change', args=[obj.user.id]),
                         obj.user.username)
    user_link.short_description = 'User'

    def user_gtd_category_badge(self, obj):
        """Show user GTD category as badge"""
        colors = {
            'actionable': 'green',
            'non_actionable': 'gray',
            'pending': 'orange',
        }
        color = colors.get(obj.user_gtd_category, 'blue')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, obj.user_gtd_category
        )
    user_gtd_category_badge.short_description = 'User GTD'

    def user_action_type_badge(self, obj):
        """Show user action type as badge"""
        colors = {
            'do': 'green',
            'delegate': 'orange',
            'defer': 'blue',
            'project': 'purple',
            'delete': 'red',
            'archive': 'gray',
            'incubate': 'teal',
            'waiting': 'yellow',
        }
        color = colors.get(obj.user_action_type, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, obj.user_action_type
        )
    user_action_type_badge.short_description = 'User Action'

    def was_correct_badge(self, obj):
        """Show correctness as badge"""
        if obj.was_correct:
            return format_html('<span style="color: green;">✓ Correct</span>')
        return format_html('<span style="color: red;">✗ Incorrect</span>')
    was_correct_badge.short_description = 'Correct'

    def has_add_permission(self, request):
        """Prevent manual addition of learning entries"""
        return False

    def has_change_permission(self, request, obj=None):
        """Prevent changes to learning entries"""
        return False


@admin.register(GTDProcessingSettings)
class GTDProcessingSettingsAdmin(admin.ModelAdmin):
    list_display = ('created_by_link', 'is_active', 'is_active_badge', 'auto_email_processing', 
                   'auto_call_queue', 'auto_chat_routing', 'updated_at')  # Added is_active to list_display
    list_filter = ('is_active', 'auto_email_processing', 'auto_call_queue', 
                  'auto_chat_routing', 'created_at', 'created_by')
    search_fields = ('created_by__username',)
    list_editable = ('is_active', 'auto_email_processing', 'auto_call_queue', 'auto_chat_routing')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 25
    list_select_related = ('created_by',)

    fieldsets = (
        ('Auto-Processing Settings', {
            'fields': ('auto_email_processing', 'auto_call_queue', 'auto_chat_routing', 'is_active')
        }),
        ('Performance Settings', {
            'fields': ('processing_interval', 'max_concurrent_items')
        }),
        ('Type-Specific Settings', {
            'fields': ('email_batch_size', 'call_queue_timeout', 'chat_response_timeout')
        }),
        ('Agent/Bot Settings', {
            'fields': ('enable_bot_cx', 'enable_bot_atc', 'enable_human_agents')
        }),
        ('Priority Settings', {
            'fields': ('auto_priority_assignment', 'priority_threshold_high', 
                      'priority_threshold_medium')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def created_by_link(self, obj):
        """Link to creator user"""
        return format_html('<a href="{}">{}</a>',
                         reverse('admin:accounts_user_change', args=[obj.created_by.id]),
                         obj.created_by.username)
    created_by_link.short_description = 'Created By'

    def is_active_badge(self, obj):
        """Show active status as badge"""
        if obj.is_active:
            return format_html('<span style="color: green;">✓ Active</span>')
        return format_html('<span style="color: gray;">✗ Inactive</span>')
    is_active_badge.short_description = 'Active'

    def save_model(self, request, obj, form, change):
        """Log settings changes"""
        super().save_model(request, obj, form, change)
        if change:
            logger.info(f"User {request.user} updated GTD processing settings (ID: {obj.id})")
        else:
            logger.info(f"User {request.user} created new GTD processing settings (ID: {obj.id})")


# ============================================================================
# UTILITY MODEL ADMINS
# ============================================================================

@admin.register(Reminder)
class ReminderAdmin(admin.ModelAdmin):
    list_display = ('title', 'remind_at', 'reminder_type_badge', 'is_sent', 'is_sent_badge', 
                   'created_by_link', 'created_at', 'related_object')  # Added is_sent to list_display
    list_filter = ('reminder_type', 'is_sent', 'remind_at', 'created_at')
    search_fields = ('title', 'description', 'created_by__username')
    list_editable = ('is_sent',)  # is_sent is now in list_display
    date_hierarchy = 'remind_at'
    readonly_fields = ('created_at',)
    list_per_page = 25
    list_select_related = ('created_by', 'task', 'project', 'event')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'remind_at', 'reminder_type', 'created_by')
        }),
        ('Related Objects', {
            'fields': ('task', 'project', 'event')
        }),
        ('Status', {
            'fields': ('is_sent',)
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def reminder_type_badge(self, obj):
        """Show reminder type as badge"""
        colors = {
            'email': 'blue',
            'push': 'green',
            'both': 'purple',
        }
        color = colors.get(obj.reminder_type, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, obj.get_reminder_type_display()
        )
    reminder_type_badge.short_description = 'Type'

    def is_sent_badge(self, obj):
        """Show sent status as badge"""
        if obj.is_sent:
            return format_html('<span style="color: green;">✓ Sent</span>')
        return format_html('<span style="color: orange;">⟳ Pending</span>')
    is_sent_badge.short_description = 'Sent'

    def created_by_link(self, obj):
        """Link to creator user"""
        return format_html('<a href="{}">{}</a>',
                         reverse('admin:accounts_user_change', args=[obj.created_by.id]),
                         obj.created_by.username)
    created_by_link.short_description = 'Created By'

    def related_object(self, obj):
        """Show related object"""
        if obj.task:
            return format_html('Task: <a href="{}">{}</a>',
                             reverse('admin:events_task_change', args=[obj.task.id]),
                             obj.task.title)
        elif obj.project:
            return format_html('Project: <a href="{}">{}</a>',
                             reverse('admin:events_project_change', args=[obj.project.id]),
                             obj.project.title)
        elif obj.event:
            return format_html('Event: <a href="{}">{}</a>',
                             reverse('admin:events_event_change', args=[obj.event.id]),
                             obj.event.title)
        return "-"
    related_object.short_description = 'Related To'

    actions = ['mark_sent', 'mark_unsent']

    def mark_sent(self, request, queryset):
        """Mark reminders as sent"""
        updated = queryset.update(is_sent=True)
        self.message_user(request, f'{updated} reminders marked as sent.')
        logger.info(f"User {request.user} marked {updated} reminders as sent")
    mark_sent.short_description = 'Mark as sent'

    def mark_unsent(self, request, queryset):
        """Mark reminders as unsent"""
        updated = queryset.update(is_sent=False)
        self.message_user(request, f'{updated} reminders marked as unsent.')
        logger.info(f"User {request.user} marked {updated} reminders as unsent")
    mark_unsent.short_description = 'Mark as unsent'


@admin.register(CreditAccount)
class CreditAccountAdmin(admin.ModelAdmin):
    list_display = ('user_link', 'balance', 'balance_formatted')
    search_fields = ('user__username',)
    readonly_fields = ('balance',)
    list_per_page = 25
    list_select_related = ('user',)
    
    fieldsets = (
        (None, {
            'fields': ('user', 'balance')
        }),
    )

    def user_link(self, obj):
        """Link to user"""
        return format_html('<a href="{}">{}</a>',
                         reverse('admin:accounts_user_change', args=[obj.user.id]),
                         obj.user.username)
    user_link.short_description = 'User'

    def balance_formatted(self, obj):
        """Format balance with currency"""
        return f"${obj.balance}"
    balance_formatted.short_description = 'Balance (Formatted)'

    actions = ['add_credits', 'subtract_credits', 'reset_balance']

    def add_credits(self, request, queryset):
        """Add credits to selected accounts"""
        amount = request.POST.get('amount', 10)
        try:
            amount = Decimal(str(amount))
            for account in queryset:
                account.add_credits(amount)
            self.message_user(request, f'Added {amount} credits to {queryset.count()} accounts.')
            logger.info(f"User {request.user} added {amount} credits to {queryset.count()} accounts")
        except Exception as e:
            logger.error(f"Error adding credits: {e}")
            self.message_user(request, f'Error: {e}', level='ERROR')
    add_credits.short_description = 'Add credits to selected accounts'

    def subtract_credits(self, request, queryset):
        """Subtract credits from selected accounts"""
        amount = request.POST.get('amount', 10)
        try:
            amount = Decimal(str(amount))
            success_count = 0
            for account in queryset:
                try:
                    account.subtract_credits(amount)
                    success_count += 1
                except ValueError as e:
                    logger.warning(f"Insufficient credits for {account.user.username}: {e}")
            self.message_user(request, f'Subtracted {amount} credits from {success_count} accounts.')
            logger.info(f"User {request.user} subtracted {amount} credits from {success_count} accounts")
        except Exception as e:
            logger.error(f"Error subtracting credits: {e}")
            self.message_user(request, f'Error: {e}', level='ERROR')
    subtract_credits.short_description = 'Subtract credits from selected accounts'

    def reset_balance(self, request, queryset):
        """Reset balance to zero"""
        updated = queryset.update(balance=Decimal('0.00'))
        self.message_user(request, f'Reset balance for {updated} accounts.')
        logger.info(f"User {request.user} reset balance for {updated} accounts")
    reset_balance.short_description = 'Reset balance to zero'


@admin.register(SystemEvent)
class SystemEventAdmin(admin.ModelAdmin):
    list_display = ('id', 'action_type', 'user_link', 'content_type', 'object_id', 'timestamp', 'summary_preview')
    list_filter = ('action_type', 'timestamp', 'user')
    search_fields = ('action_type', 'summary', 'metadata', 'user__username')
    date_hierarchy = 'timestamp'
    readonly_fields = ('timestamp', 'user_link', 'content_type', 'object_id', 'summary', 'metadata')
    list_per_page = 50
    list_select_related = ('user', 'content_type')

    fieldsets = (
        ('Event Information', {
            'fields': ('action_type', 'summary', 'timestamp')
        }),
        ('Related Object', {
            'fields': ('user', 'content_type', 'object_id')
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
    )

    def user_link(self, obj):
        """Link to user if exists"""
        if obj.user:
            return format_html('<a href="{}">{}</a>',
                             reverse('admin:accounts_user_change', args=[obj.user.id]),
                             obj.user.username)
        return "system"
    user_link.short_description = 'User'
    user_link.admin_order_field = 'user__username'

    def summary_preview(self, obj):
        """Truncated summary preview"""
        return obj.summary[:75] + '...' if obj.summary and len(obj.summary) > 75 else obj.summary
    summary_preview.short_description = 'Summary'

    def has_add_permission(self, request):
        """Prevent manual addition of system events"""
        return False

    def has_change_permission(self, request, obj=None):
        """Prevent changes to system events"""
        return False

    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of system events"""
        return False

