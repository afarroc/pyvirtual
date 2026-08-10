from django.contrib import admin
from .models import (
    PlayerProfile, Room, RoomConnection, RoomObject, Box,
    EntranceExit, Portal, Comment, Evaluation,
    RoomMember, Message, Outbox, CDC
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
            'fields': ('position_x', 'position_y')
        }),
        ('Stats', {
            'fields': ('energy', 'productivity', 'social', 'skills')
        }),
        ('Timestamps', {
            'fields': ('last_interaction', 'last_state_change'),
            'classes': ('collapse',)
        }),
    )

@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('name', 'room_type', 'owner', 'permissions', 'rating', 'capacity', 'created_at')
    list_filter = ('room_type', 'permissions', 'created_at')
    search_fields = ('name', 'description', 'owner__username')
    filter_horizontal = ('administrators', 'portals')
    readonly_fields = ('created_at', 'updated_at', 'bumped_at')
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'owner', 'creator', 'room_type')
        }),
        ('Settings', {
            'fields': ('permissions', 'capacity', 'rating')
        }),
        ('Dimensions', {
            'fields': ('x', 'y', 'z', 'length', 'width', 'height'),
            'classes': ('collapse',)
        }),
        ('Orientation', {
            'fields': ('pitch', 'yaw', 'roll'),
            'classes': ('collapse',)
        }),
        ('Relations', {
            'fields': ('administrators', 'parent_room', 'portals'),
            'classes': ('collapse',)
        }),
        ('Media', {
            'fields': ('image',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'bumped_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(RoomConnection)
class RoomConnectionAdmin(admin.ModelAdmin):
    list_display = ('id', 'from_room', 'to_room', 'entrance', 'bidirectional', 'energy_cost')
    list_filter = ('bidirectional',)
    search_fields = ('from_room__name', 'to_room__name', 'entrance__name')

@admin.register(RoomObject)
class RoomObjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'room', 'object_type', 'position_x', 'position_y')
    list_filter = ('object_type', 'room')
    search_fields = ('name', 'room__name')
    readonly_fields = ('effect',)

@admin.register(Box)
class BoxAdmin(admin.ModelAdmin):
    list_display = ('name', 'room', 'is_open', 'is_locked', 'mass', 'capacity', 'updated_at')
    list_filter = ('is_open', 'is_locked', 'material_type', 'room')
    search_fields = ('name', 'room__name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('name', 'room', 'description')
        }),
        ('Position', {
            'fields': ('position_x', 'position_y')
        }),
        ('Dimensions', {
            'fields': ('width', 'height', 'depth', 'mass')
        }),
        ('Appearance', {
            'fields': ('color', 'material_type', 'image'),
            'classes': ('collapse',)
        }),
        ('State', {
            'fields': ('is_open', 'is_locked', 'required_key')
        }),
        ('Inventory', {
            'fields': ('capacity', 'contents'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(EntranceExit)
class EntranceExitAdmin(admin.ModelAdmin):
    list_display = ('name', 'room', 'face', 'position_x', 'position_y', 'enabled')
    list_filter = ('face', 'enabled')
    search_fields = ('name', 'room__name')
    readonly_fields = ('connection',)

@admin.register(Portal)
class PortalAdmin(admin.ModelAdmin):
    list_display = ('name', 'entrance', 'exit', 'energy_cost', 'cooldown')
    search_fields = ('name', 'entrance__room__name', 'exit__room__name')

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

@admin.register(RoomMember)
class RoomMemberAdmin(admin.ModelAdmin):
    list_display = ('room', 'user', 'joined_at')
    list_filter = ('room', 'joined_at')
    search_fields = ('room__name', 'user__username')
    date_hierarchy = 'joined_at'

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('room', 'user', 'created_at', 'short_content')
    list_filter = ('room', 'created_at')
    search_fields = ('room__name', 'user__username', 'content')
    date_hierarchy = 'created_at'
    
    def short_content(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    short_content.short_description = 'Content Preview'

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