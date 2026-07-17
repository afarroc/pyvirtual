"""Administración de usuarios para Management360.

Registra el modelo de usuario personalizado (accounts.User) en el admin de
Django, exponiendo los campos propios (teléfono, avatar, fechas) además de
los campos estándar de AbstractUser.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin de usuarios personalizado para accounts.User."""

    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "phone",
        "is_staff",
        "is_active",
        "is_superuser",
        "created_at",
    )
    list_filter = BaseUserAdmin.list_filter + ("phone",)
    search_fields = ("username", "email", "first_name", "last_name", "phone")
    ordering = ("username",)

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (_("Información personal"), {
            "fields": (
                "first_name",
                "last_name",
                "email",
                "phone",
                "avatar",
            )
        }),
        (_("Permisos"), {
            "fields": (
                "is_active",
                "is_staff",
                "is_superuser",
                "groups",
                "user_permissions",
            )
        }),
        (_("Fechas importantes"), {"fields": ("last_login", "created_at", "updated_at")}),
    )

    readonly_fields = ("created_at", "updated_at")

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "username",
                "email",
                "phone",
                "password1",
                "password2",
            ),
        }),
    )
