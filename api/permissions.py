from __future__ import annotations

from django.conf import settings
from rest_framework import permissions


class IsWriteAuthenticated(permissions.BasePermission):
    """
    - Lectura (GET/HEAD/OPTIONS): acepta sesión Django o Bearer token.
    - Escritura (POST/PATCH/PUT/DELETE): acepta sesión Django o Bearer token.
    """

    def has_permission(self, request, view):
        if request.user and request.user.is_authenticated:
            return True

        auth = request.META.get('HTTP_AUTHORIZATION', '')
        if auth.startswith('Bearer '):
            token = auth.split(' ', 1)[1].strip()
            expected = getattr(settings, 'M360_API_KEY', '')
            return bool(expected and token == expected)

        return False
