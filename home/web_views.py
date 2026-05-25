from django.contrib import messages
from django.shortcuts import redirect
from django.views.generic import TemplateView

from core.mixins import PortalAccessRequiredMixin

from .models import AppRelease


class AppReleaseView(PortalAccessRequiredMixin, TemplateView):
    template_name = 'manager/app_release.html'

    def dispatch(self, request, *args, **kwargs):
        if not (request.user.is_superuser or getattr(request.user, 'role', None) == 'super_manager'):
            return redirect('manager:dashboard')
        return super().dispatch(request, *args, **kwargs)

    MAX_RELEASES = 2

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['releases'] = list(AppRelease.objects.all()[:self.MAX_RELEASES])
        return ctx

    def post(self, request, *args, **kwargs):
        apk_file = request.FILES.get('apk')
        version  = request.POST.get('version', '').strip()
        notes    = request.POST.get('notes', '').strip()

        if not apk_file:
            messages.error(request, 'Debes seleccionar un archivo APK.')
            return redirect('manager:app_release')

        AppRelease.objects.create(apk=apk_file, version=version, notes=notes)

        # Elimina los registros más antiguos que excedan el límite, con sus archivos
        all_ids = list(AppRelease.objects.values_list('pk', flat=True))
        if len(all_ids) > self.MAX_RELEASES:
            to_delete = AppRelease.objects.filter(pk__in=all_ids[self.MAX_RELEASES:])
            for old in to_delete:
                if old.apk:
                    old.apk.delete(save=False)
            to_delete.delete()

        messages.success(request, f'App{" v" + version if version else ""} publicada correctamente.')
        return redirect('manager:app_release')
