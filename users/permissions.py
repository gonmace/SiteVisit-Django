from rest_framework.permissions import BasePermission

from users.models import User


def _is_su(user) -> bool:
    return bool(user and user.is_authenticated and user.is_superuser)


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return _is_su(request.user)


class IsTechnician(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated
                    and (request.user.role == User.Role.TECHNICIAN or _is_su(request.user)))


class IsPortalUser(BasePermission):
    """Permite MANAGER, SUPER_MANAGER y superuser (equivalente al portal web)."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated
                    and (request.user.role in (User.Role.MANAGER, User.Role.SUPER_MANAGER)
                         or _is_su(request.user)))


class IsSuperManager(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated
                    and (request.user.role == User.Role.SUPER_MANAGER or _is_su(request.user)))


class IsViewer(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated
                    and (request.user.role == User.Role.VIEWER or _is_su(request.user)))


class IsDashboardConsumer(BasePermission):
    """Permite MANAGER, SUPER_MANAGER, VIEWER y superuser."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated
                    and (request.user.role in (
                        User.Role.MANAGER, User.Role.SUPER_MANAGER, User.Role.VIEWER,
                    ) or _is_su(request.user)))


class IsSameCompanyOrPrivileged(BasePermission):
    """Object-level: pasa si superuser, si es portal user, o si la empresa coincide."""

    def has_object_permission(self, request, view, obj):
        if _is_su(request.user):
            return True
        if request.user.role in (User.Role.MANAGER, User.Role.SUPER_MANAGER):
            return True
        target_company = getattr(obj, 'company', None)
        return target_company == request.user.company


class IsPortalOrTechnician(BasePermission):
    """Permite TECHNICIAN, MANAGER, SUPER_MANAGER y superuser — bloquea VIEWER."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated
                    and (request.user.role in (
                        User.Role.TECHNICIAN, User.Role.MANAGER, User.Role.SUPER_MANAGER,
                    ) or _is_su(request.user)))

