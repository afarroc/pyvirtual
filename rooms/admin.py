from django.contrib import admin
from .models import (
    PlayerProfile, Cell, CellConnection,
    Comment, Evaluation, Message, Outbox, CDC
)


@admin.register(PlayerProfile)
class PlayerProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'current_room', 'state', 'energy', 'productivity', 'social', 'last_state_change')
    list_filter = ('state', 'current_room')
    search_fields = ('user__username', 'skills')
    readonly_fields = ('last_interaction', 'last_state_change')
    fieldsets = (
        (None, {
            'fields': ('user', 'current_room', 'state')
        }),
        ('Position', {
            'fields': ('position_x', 'position_y', 'position_z')
        }),
        ('Stats', {
            'fields': ('energy', 'productivity', 'social', 'skills')
        }),
        ('Timestamps', {
            'fields': ('last_interaction', 'last_state_change'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Cell)
class CellAdmin(admin.ModelAdmin):
    list_display = ('name', 'cell_type', 'owner', 'is_active', 'position_x', 'position_y', 'position_z', 'parent', 'capacity', 'is_locked')
    list_filter = ('cell_type', 'is_active', 'is_locked', 'material_type', 'owner')
    search_fields = ('name', 'description', 'owner__username')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('name', 'cell_type', 'owner', 'is_active', 'parent')
        }),
        ('Position', {
            'fields': ('position_x', 'position_y', 'position_z')
        }),
        ('Dimensions', {
            'fields': ('length', 'width', 'height', 'depth'),
            'classes': ('collapse',)
        }),
        ('Appearance', {
            'fields': ('color', 'color_primary', 'color_secondary', 'material_type', 'image'),
            'classes': ('collapse',)
        }),
        ('Container', {
            'fields': ('capacity', 'contents', 'is_open', 'is_locked', 'required_key', 'mass', 'effect'),
            'classes': ('collapse',)
        }),
        ('Media', {
            'fields': ('description',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(CellConnection)
class CellConnectionAdmin(admin.ModelAdmin):
    list_display = ('id', 'from_cell', 'to_cell', 'entrance', 'bidirectional', 'energy_cost')
    list_filter = ('bidirectional',)
    search_fields = ('from_cell__name', 'to_cell__name', 'entrance__name')


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('room', 'user', 'created_at', 'short_content')
    list_filter = ('room', 'created_at')
    search_fields = ('room__name', 'user__username', 'content')
    date_hierarchy = 'created_at'

    def short_content(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    short_content.short_description = 'Content Preview'


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'room', 'created_at', 'short_comment')
    list_filter = ('room', 'created_at')
    search_fields = ('user__username', 'room__name', 'comment')
    date_hierarchy = 'created_at'

    def short_comment(self, obj):
        return obj.comment[:50] + '...' if len(obj.comment) > 50 else obj.comment
    short_comment.short_description = 'Comment Preview'


@admin.register(Evaluation)
class EvaluationAdmin(admin.ModelAdmin):
    list_display = ('user', 'room', 'rating', 'created_at', 'short_comment')
    list_filter = ('rating', 'room', 'created_at')
    search_fields = ('user__username', 'room__name', 'comment')

    def short_comment(self, obj):
        return obj.comment[:50] + '...' if len(obj.comment) > 50 else obj.comment
    short_comment.short_description = 'Comment Preview'


@admin.register(Outbox)
class OutboxAdmin(admin.ModelAdmin):
    list_display = ('id', 'method', 'partition', 'created_at')
    list_filter = ('method', 'partition', 'created_at')
    search_fields = ('payload',)
    date_hierarchy = 'created_at'


@admin.register(CDC)
class CDCAdmin(admin.ModelAdmin):
    list_display = ('id', 'method', 'partition', 'created_at')
    list_filter = ('method', 'partition', 'created_at')
    search_fields = ('payload',)
    date_hierarchy = 'created_at'
