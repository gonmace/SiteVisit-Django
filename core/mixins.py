from django.contrib.auth import logout as auth_logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect

from users.models import User
from visits.models import Visit


class ManagerRequiredMixin(LoginRequiredMixin):
    """Allow only manager and super_manager roles. Includes _base_queryset for visit filtering."""

    login_url = '/manager/login/'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if request.user.role not in (User.Role.MANAGER, User.Role.SUPER_MANAGER):
            return redirect(self.login_url)
        if not request.user.is_active:
            auth_logout(request)
            return redirect(self.login_url)
        return super().dispatch(request, *args, **kwargs)

    def _base_queryset(self):
        qs = Visit.objects.select_related(
            'technician', 'technician__profile_photo', 'site',
        ).prefetch_related('photos', 'tracking_points')
        if self.request.user.role == User.Role.MANAGER:
            qs = qs.filter(technician__company=self.request.user.company)
        return qs
