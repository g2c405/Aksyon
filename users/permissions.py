from rest_framework.permissions import BasePermission
from django.contrib.auth import get_user_model
User = get_user_model()
from core.choices import Role
class IsUser(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == Role.USER
        )


class IsAdmin(BasePermission):

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == Role.ADMIN
        )


class IsPrivilegedAdmin(BasePermission):

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == Role.PRIVILEGED_ADMIN
        )