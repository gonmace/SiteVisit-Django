from django.contrib.auth import logout as auth_logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect

from users.models import User
from visits.models import Visit


class _RoleGatedMixin(LoginRequiredMixin):
    """Base interna. Subclases declaran `allowed_roles`."""

    login_url = '/manager/login/'
    allowed_roles: tuple = ()

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.is_active:
            auth_logout(request)
            return redirect(self.login_url)
        if request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)
        if request.user.role not in self.allowed_roles:
            return redirect('manager:visits_approval')
        return super().dispatch(request, *args, **kwargs)


class PortalAccessRequiredMixin(_RoleGatedMixin):
    """Permite MANAGER, SUPER_MANAGER y superuser al portal /manager/."""

    allowed_roles = (User.Role.MANAGER, User.Role.SUPER_MANAGER)


class SuperManagerRequiredMixin(_RoleGatedMixin):
    """Permite solo SUPER_MANAGER y superuser."""

    allowed_roles = (User.Role.SUPER_MANAGER,)


class SuperuserOnlyMixin(LoginRequiredMixin):
    """Permite exclusivamente al superusuario de Django."""

    login_url = '/manager/login/'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.is_superuser:
            return redirect('manager:visits_approval')
        return super().dispatch(request, *args, **kwargs)



class CompanyScopedQuerysetMixin:
    """Mixin de queryset (sin auth) para filtrado opcional de empresa vía ?company=."""

    def get_company_filter(self) -> str:
        company = self.request.GET.get('company', '').lower().strip()
        valid = [c for c, _ in User.Company.choices]
        return company if company in valid else ''

    def apply_company_filter(self, qs, lookup: str):
        company = self.get_company_filter()
        if company:
            return qs.filter(**{lookup: company})
        return qs

    def company_context(self) -> dict:
        return {
            'company_filter': self.get_company_filter(),
            'company_choices': User.Company.choices,
        }


class VisitsBaseQuerysetMixin:
    """Queryset base de Visit sin ningún filtro de empresa."""

    def base_visit_queryset(self):
        return Visit.objects.select_related(
            'technician', 'technician__profile_photo', 'site',
        ).prefetch_related('photos', 'tracking_points')

    # Alias para compatibilidad con código que aún use _base_queryset
    def _base_queryset(self):
        return self.base_visit_queryset()
