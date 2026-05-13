from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, ListView

from sites.models import Site
from users.models import User
from visits.models import Visit


class ManagerRequiredMixin(LoginRequiredMixin):
    """Allow only manager and super_manager roles."""

    login_url = '/manager/login/'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if request.user.role not in (User.Role.MANAGER, User.Role.SUPER_MANAGER):
            return redirect(self.login_url)
        if not request.user.is_active:
            from django.contrib.auth import logout as auth_logout
            auth_logout(request)
            return redirect(self.login_url)
        return super().dispatch(request, *args, **kwargs)

    def _base_queryset(self):
        qs = Visit.objects.select_related('technician', 'technician__profile_photo', 'site').prefetch_related('photos', 'tracking_points')
        if self.request.user.role == User.Role.MANAGER:
            qs = qs.filter(technician__company=self.request.user.company)
        return qs


class VisitsApprovalView(ManagerRequiredMixin, ListView):
    template_name = 'manager/visits_approval.html'
    context_object_name = 'visits'
    paginate_by = 30

    _VALID_TABS = ('planificados', 'programados', 'en_ejecucion', 'concluidos', 'cancelados')

    def _get_tab(self):
        default = 'planificados' if self.request.user.role == User.Role.SUPER_MANAGER else 'programados'
        tab = self.request.GET.get('tab', default)
        return tab if tab in self._VALID_TABS else default

    def get_queryset(self):
        qs = self._base_queryset().select_related('coordinator')
        tab = self._get_tab()
        if tab == 'planificados':
            return qs.filter(status=Visit.Status.PENDIENTE_APROBACION).order_by('-created_at')
        if tab == 'programados':
            return qs.filter(status=Visit.Status.PROGRAMADA).order_by('scheduled_date')
        if tab == 'en_ejecucion':
            return qs.filter(status__in=[
                Visit.Status.EN_CAMINO, Visit.Status.LLEGADA,
                Visit.Status.TRABAJANDO, Visit.Status.FINALIZANDO,
            ]).order_by('-scheduled_date')
        if tab == 'concluidos':
            return qs.filter(status=Visit.Status.COMPLETADA).order_by('-scheduled_date')
        # cancelados
        return qs.filter(status__in=[
            Visit.Status.CANCELADA, Visit.Status.RECHAZADA,
        ]).order_by('-scheduled_date')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        base = self._base_queryset()
        ctx['tab'] = self._get_tab()
        ctx['pending_count']      = base.filter(status=Visit.Status.PENDIENTE_APROBACION).count()
        ctx['programados_count']  = base.filter(status=Visit.Status.PROGRAMADA).count()
        ctx['en_ejecucion_count'] = base.filter(status__in=[
            Visit.Status.EN_CAMINO, Visit.Status.LLEGADA,
            Visit.Status.TRABAJANDO, Visit.Status.FINALIZANDO,
        ]).count()
        ctx['concluidos_count']   = base.filter(status=Visit.Status.COMPLETADA).count()
        ctx['cancelados_count']   = base.filter(status__in=[
            Visit.Status.CANCELADA, Visit.Status.RECHAZADA,
        ]).count()
        ctx['total_count'] = base.count()
        return ctx


class VisitDetailWebView(ManagerRequiredMixin, DetailView):
    template_name = 'manager/visit_detail.html'
    context_object_name = 'visit'

    def get_object(self):
        return get_object_or_404(self._base_queryset(), pk=self.kwargs['pk'])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        v = ctx['visit']
        ctx['visit_number'] = Visit.objects.filter(technician=v.technician, pk__lte=v.pk).count()
        if v.hora_inicio_trabajos and v.hora_fin_trabajos:
            delta = v.hora_fin_trabajos - v.hora_inicio_trabajos
            total = int(delta.total_seconds())
            h, remainder = divmod(total, 3600)
            m, s = divmod(remainder, 60)
            ctx['visit_duration'] = f'{h}h {m:02d}m' if h else f'{m}m {s:02d}s'
        else:
            ctx['visit_duration'] = '—'
        ctx['site_geo'] = {
            'lat': v.site.latitude,
            'lng': v.site.longitude,
            'code': v.site.code,
            'name': v.site.name,
        }
        ctx['tracking_points_geo'] = [
            {
                'lat': p.latitude,
                'lng': p.longitude,
                'event': p.event,
                'event_display': p.get_event_display(),
                'timestamp': p.timestamp.isoformat(),
            }
            for p in v.tracking_points.all()
        ]
        return ctx



class VisitCreateWebView(ManagerRequiredMixin, View):
    template_name = 'manager/visit_form.html'

    def _technicians(self, request):
        qs = User.objects.filter(role=User.Role.TECHNICIAN, status=User.Status.ACTIVE).order_by('first_name', 'last_name')
        if request.user.role == User.Role.MANAGER:
            qs = qs.filter(company=request.user.company)
        return qs

    def _sites(self, request):
        qs = Site.objects.order_by('code')
        if request.user.role == User.Role.MANAGER:
            qs = qs.filter(company=request.user.company)
        return qs

    def get(self, request):
        return self._render(request)

    def post(self, request):
        technician_id   = request.POST.get('technician')
        site_id         = request.POST.get('site')
        scheduled_date  = request.POST.get('scheduled_date')
        reason          = request.POST.get('reason', '').strip()

        errors = {}
        if not technician_id:
            errors['technician'] = 'Selecciona un técnico.'
        if not site_id:
            errors['site'] = 'Selecciona un sitio.'
        if not scheduled_date:
            errors['scheduled_date'] = 'Indica la fecha programada.'
        if not reason:
            errors['reason'] = 'El motivo es obligatorio.'

        technician = None
        site = None
        if technician_id:
            try:
                technician = self._technicians(request).get(pk=technician_id)
            except User.DoesNotExist:
                errors['technician'] = 'Técnico no válido.'
        if site_id:
            try:
                site = self._sites(request).get(pk=site_id)
            except Site.DoesNotExist:
                errors['site'] = 'Sitio no válido.'

        if errors:
            return self._render(request, errors=errors, post=request.POST)

        is_super = request.user.role == User.Role.SUPER_MANAGER
        visit = Visit.objects.create(
            technician     = technician,
            site           = site,
            coordinator    = request.user,
            status         = Visit.Status.PROGRAMADA if is_super else Visit.Status.PENDIENTE_APROBACION,
            approved_by    = request.user if is_super else None,
            approved_at    = timezone.now() if is_super else None,
            reason         = reason,
            scheduled_date = scheduled_date,
        )
        if is_super:
            msg = f'Servicio #{visit.pk} creado y aprobado automáticamente.'
        else:
            msg = f'Servicio #{visit.pk} creado. Pendiente de aprobación del manager.'
        messages.success(request, msg)
        return redirect('manager:visit_detail', pk=visit.pk)

    def _render(self, request, errors=None, post=None):
        from django.shortcuts import render
        return render(request, self.template_name, {
            'technicians': self._technicians(request),
            'sites':       self._sites(request),
            'errors':      errors or {},
            'post':        post or {},
        })



class VisitUpdateWebView(ManagerRequiredMixin, View):
    template_name = 'manager/visit_form.html'

    def _get_visit(self, request, pk):
        qs = Visit.objects.filter(
            pk=pk,
            status=Visit.Status.PENDIENTE_APROBACION,
        ).select_related('site', 'technician')
        if request.user.role == User.Role.MANAGER:
            qs = qs.filter(technician__company=request.user.company)
        return get_object_or_404(qs)

    def _technicians(self, request):
        qs = User.objects.filter(role=User.Role.TECHNICIAN, status=User.Status.ACTIVE).order_by('first_name', 'last_name')
        if request.user.role == User.Role.MANAGER:
            qs = qs.filter(company=request.user.company)
        return qs

    def get(self, request, pk):
        visit = self._get_visit(request, pk)
        return self._render(request, visit)

    def post(self, request, pk):
        visit = self._get_visit(request, pk)
        technician_id  = request.POST.get('technician')
        site_id        = request.POST.get('site')
        scheduled_date = request.POST.get('scheduled_date')
        reason         = request.POST.get('reason', '').strip()

        errors = {}
        if not technician_id:
            errors['technician'] = 'Selecciona un técnico.'
        if not site_id:
            errors['site'] = 'Selecciona un sitio.'
        if not scheduled_date:
            errors['scheduled_date'] = 'Indica la fecha programada.'
        if not reason:
            errors['reason'] = 'El motivo es obligatorio.'

        technician = site = None
        if technician_id:
            try:
                technician = self._technicians(request).get(pk=technician_id)
            except User.DoesNotExist:
                errors['technician'] = 'Técnico no válido.'
        if site_id:
            try:
                site = Site.objects.get(pk=site_id)
            except Site.DoesNotExist:
                errors['site'] = 'Sitio no válido.'

        if errors:
            return self._render(request, visit, errors=errors, post=request.POST, error_site=site)

        visit.technician     = technician
        visit.site           = site
        visit.scheduled_date = scheduled_date
        visit.reason         = reason
        visit.save(update_fields=['technician', 'site', 'scheduled_date', 'reason'])
        messages.success(request, f'Servicio #{visit.pk} actualizado.')
        return redirect('manager:visits_approval')

    def _render(self, request, visit, errors=None, post=None, error_site=None):
        from django.shortcuts import render
        if post:
            initial_site = error_site
        else:
            initial_site = visit.site
        return render(request, self.template_name, {
            'technicians':   self._technicians(request),
            'errors':        errors or {},
            'post':          post or {
                'technician':     str(visit.technician_id),
                'site':           str(visit.site_id),
                'scheduled_date': str(visit.scheduled_date),
                'reason':         visit.reason,
            },
            'initial_site': initial_site,
            'is_edit':      True,
            'visit':        visit,
        })


class VisitDeleteView(ManagerRequiredMixin, View):
    def post(self, request, pk):
        if request.user.role != User.Role.SUPER_MANAGER:
            messages.error(request, 'Solo el super manager puede eliminar servicios.')
            return redirect('manager:visits_approval')

        visit = get_object_or_404(
            self._base_queryset().filter(
                status__in=[Visit.Status.CANCELADA, Visit.Status.RECHAZADA]
            ),
            pk=pk,
        )
        visit.delete()
        messages.success(request, f'Servicio #{pk} eliminado.')
        return redirect(reverse('manager:visits_approval') + '?tab=cancelados')


class VisitCancelView(ManagerRequiredMixin, View):
    def post(self, request, pk):
        if request.user.role != User.Role.MANAGER:
            messages.error(request, 'Solo el coordinador puede cancelar servicios.')
            return redirect('manager:visits_approval')

        reason = (request.POST.get('cancellation_reason') or '').strip()
        if not reason:
            messages.error(request, 'Debes indicar un motivo de cancelación.')
            return redirect(reverse('manager:visits_approval') + '?tab=planificados')

        qs = Visit.objects.filter(
            pk=pk,
            status=Visit.Status.PENDIENTE_APROBACION,
            technician__company=request.user.company,
        )
        visit = get_object_or_404(qs)

        visit.status = Visit.Status.CANCELADA
        visit.notas  = reason
        visit.save(update_fields=['status', 'notas'])
        messages.success(request, f'Servicio #{pk} cancelado.')
        return redirect(reverse('manager:visits_approval') + '?tab=planificados')


class VisitApproveView(ManagerRequiredMixin, View):
    def post(self, request, pk):
        if request.user.role != User.Role.SUPER_MANAGER:
            messages.error(request, 'Solo el manager puede aprobar servicios.')
            return redirect('manager:visits_approval')

        visit = get_object_or_404(self._base_queryset(), pk=pk)
        if visit.status != Visit.Status.PENDIENTE_APROBACION:
            messages.warning(request, 'El servicio ya no está pendiente de aprobación.')
            return redirect('manager:visit_detail', pk=pk)

        visit.status      = Visit.Status.PROGRAMADA
        visit.approved_by = request.user
        visit.approved_at = timezone.now()
        visit.save(update_fields=['status', 'approved_by', 'approved_at'])
        messages.success(request, f'Servicio #{pk} aprobado. Técnico programado.')
        return redirect(reverse('manager:visits_approval') + '?tab=planificados')


class VisitRejectView(ManagerRequiredMixin, View):
    def post(self, request, pk):
        if request.user.role != User.Role.SUPER_MANAGER:
            messages.error(request, 'Solo el manager puede rechazar servicios.')
            return redirect('manager:visits_approval')

        reason = (request.POST.get('rejection_reason') or '').strip()
        if not reason:
            messages.error(request, 'Debes indicar un motivo de rechazo.')
            return redirect(reverse('manager:visits_approval') + '?tab=planificados')

        visit = get_object_or_404(self._base_queryset(), pk=pk)
        if visit.status != Visit.Status.PENDIENTE_APROBACION:
            messages.warning(request, 'El servicio ya no está pendiente de aprobación.')
            return redirect('manager:visit_detail', pk=pk)

        visit.status           = Visit.Status.RECHAZADA
        visit.rejected_by      = request.user
        visit.rejected_at      = timezone.now()
        visit.rejection_reason = reason
        visit.save(update_fields=['status', 'rejected_by', 'rejected_at', 'rejection_reason'])
        messages.success(request, f'Servicio #{pk} rechazado.')
        return redirect(reverse('manager:visits_approval') + '?tab=planificados')
