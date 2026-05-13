from rest_framework.permissions import BasePermission

from users.models import User


class IsTechnician(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated
                    and request.user.role == User.Role.TECHNICIAN)


class IsManager(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated
                    and request.user.role in (User.Role.MANAGER, User.Role.SUPER_MANAGER))


class IsSuperManager(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated
                    and request.user.role == User.Role.SUPER_MANAGER)


class IsViewer(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated
                    and request.user.role == User.Role.VIEWER)


class IsSameCompanyOrSuperManager(BasePermission):
    """Object-level: pasa si el target es de la misma empresa o el solicitante es super_manager."""

    def has_object_permission(self, request, view, obj):
        if request.user.role == User.Role.SUPER_MANAGER:
            return True
        target_company = getattr(obj, 'company', None)
        return target_company == request.user.company
