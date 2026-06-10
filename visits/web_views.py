import io
import json
import os
import zipfile

from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import DetailView, ListView
from django.views.decorators.csrf import csrf_exempt

from core.mixins import (
    PortalAccessRequiredMixin, SuperManagerRequiredMixin,
    VisitsBaseQuerysetMixin, CompanyScopedQuerysetMixin,
)
from sites.models import Site
from users.models import User
from visits.models import Visit

MOBILE_LIMIT  = 10
DESKTOP_LIMIT = 20


class VisitsApprovalView(PortalAccessRequiredMixin, VisitsBaseQuerysetMixin, CompanyScopedQuerysetMixin, ListView):
    template_name = 'manager/visits_approval.html'
    context_object_name = 'visits'

    _VALID_TABS = ('planificados', 'programados', 'en_ejecucion', 'concluidos', 'cancelados')

    def _get_tab(self):
        is_sm = (
            self.request.user.role == User.Role.SUPER_MANAGER
            or self.request.user.is_superuser
        )
        default = 'planificados' if is_sm else 'programados'
        tab = self.request.GET.get('tab', default)
        return tab if tab in self._VALID_TABS else default

    def _is_desktop(self):
        return self.request.COOKIES.get('vp') == 'd'

    def _get_limit(self):
        try:
            limit = int(self.request.GET.get('limit', ''))
            if 1 <= limit <= DESKTOP_LIMIT:
                return limit
        except (ValueError, TypeError):
            pass
        return DESKTOP_LIMIT if self._is_desktop() else MOBILE_LIMIT

    def _get_offset(self):
        try:
            return max(0, int(self.request.GET.get('offset', 0)))
        except (ValueError, TypeError):
            return 0

    def _apply_filters(self, qs):
        site_q = self.request.GET.get('q', '').strip()
        qs = self.apply_company_filter(qs, 'technician__company')
        if site_q:
            qs = qs.filter(
                Q(site__code__icontains=site_q) |
                Q(site__operator_code__icontains=site_q) |
                Q(site__name__icontains=site_q) |
                Q(reason__icontains=site_q) |
                Q(notas__icontains=site_q) |
                Q(rejection_reason__icontains=site_q)
            )
        return qs

    def get_queryset(self):
        qs = self._apply_filters(self.base_visit_queryset().select_related('coordinator'))
        tab = self._get_tab()
        if tab == 'planificados':
            return qs.filter(status=Visit.Status.PENDIENTE_APROBACION).order_by('-created_at', '-pk')
        if tab == 'programados':
            return qs.filter(status=Visit.Status.PROGRAMADA).order_by('scheduled_date', 'pk')
        if tab == 'en_ejecucion':
            return qs.filter(status__in=[
                Visit.Status.EN_CAMINO, Visit.Status.LLEGADA,
                Visit.Status.TRABAJANDO, Visit.Status.FINALIZANDO,
            ]).order_by('-scheduled_date', '-pk')
        if tab == 'concluidos':
            return qs.filter(status=Visit.Status.COMPLETADA).order_by('-scheduled_date', '-pk')
        # cancelados
        return qs.filter(status__in=[
            Visit.Status.CANCELADA, Visit.Status.RECHAZADA,
        ]).order_by('-scheduled_date', '-pk')

    def _partials_for_tab(self, tab):
        prefix = 'planificados' if tab == 'planificados' else 'generic'
        return (
            f'manager/partials/visits_{prefix}_cards.html',
            f'manager/partials/visits_{prefix}_rows.html',
            f'manager/partials/visits_{prefix}_thead.html',
        )

    def get(self, request, *args, **kwargs):
        offset = self._get_offset()
        limit  = self._get_limit()
        tab    = self._get_tab()

        qs = self.get_queryset()
        tab_total = qs.count()
        items = list(qs[offset:offset + limit + 1])
        has_more = len(items) > limit
        visits = items[:limit]
        shown = offset + len(visits)

        cards_tpl, rows_tpl, thead_tpl = self._partials_for_tab(tab)

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            ctx = {'visits': visits, 'tab': tab}
            return JsonResponse({
                'cards_html':  render_to_string(cards_tpl, ctx, request),
                'rows_html':   render_to_string(rows_tpl, ctx, request),
                'has_more':    has_more,
                'next_offset': shown,
                'tab_total':   tab_total,
            })

        self.object_list = visits
        ctx = self.get_context_data(**kwargs)
        ctx.update({
            'has_more':     has_more,
            'next_offset':  shown,
            'tab_total':    tab_total,
            'limit':        limit,
            'mobile_limit': MOBILE_LIMIT,
            'desktop_limit': DESKTOP_LIMIT,
            'cards_tpl':    cards_tpl,
            'rows_tpl':     rows_tpl,
            'thead_tpl':    thead_tpl,
        })
        return self.render_to_response(ctx)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        base = self._apply_filters(self.base_visit_queryset())
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
        ctx['site_q'] = self.request.GET.get('q', '')
        ctx['can_approve'] = (
            self.request.user.role == User.Role.SUPER_MANAGER
            or self.request.user.is_superuser
        )
        ctx.update(self.company_context())
        return ctx


class VisitDetailWebView(PortalAccessRequiredMixin, VisitsBaseQuerysetMixin, DetailView):
    template_name = 'manager/visit_detail.html'
    context_object_name = 'visit'

    def get_object(self):
        return get_object_or_404(self.base_visit_queryset(), pk=self.kwargs['pk'])

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
        points = list(v.tracking_points.all())
        tracking_steps = []
        for i, p in enumerate(points):
            elapsed = None
            if i > 0:
                delta = int((p.timestamp - points[i - 1].timestamp).total_seconds())
                if delta < 60:
                    elapsed = '< 1 min'
                elif delta < 3600:
                    elapsed = f'{delta // 60} min'
                else:
                    h = delta // 3600
                    m = (delta % 3600) // 60
                    elapsed = f'{h}h {m:02d}m' if m else f'{h}h'
            tracking_steps.append({
                'event':         p.event,
                'event_display': p.get_event_display(),
                'timestamp':     p.timestamp,
                'latitude':      p.latitude,
                'longitude':     p.longitude,
                'elapsed':       elapsed,
            })
        ctx['tracking_steps'] = tracking_steps
        ctx['tracking_points_geo'] = [
            {
                'lat': p.latitude,
                'lng': p.longitude,
                'event': p.event,
                'event_display': p.get_event_display(),
                'timestamp': p.timestamp.isoformat(),
            }
            for p in points
        ]
        return ctx



class VisitFormMixin:
    """Shared queryset helpers for visit create/edit views."""

    def _technicians(self, request):
        return User.objects.filter(
            role=User.Role.TECHNICIAN, status=User.Status.ACTIVE,
        ).order_by('first_name', 'last_name')


class VisitCreateWebView(VisitFormMixin, PortalAccessRequiredMixin, View):
    template_name = 'manager/visit_form.html'

    def _sites(self, request):
        return Site.objects.order_by('code')

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

        is_super = (
            request.user.role == User.Role.SUPER_MANAGER or request.user.is_superuser
        )
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
            from notifications.models import Notification
            from notifications.services import notify_supervisors
            notify_supervisors(
                event=Notification.Event.VISIT_PENDING,
                title=f'Servicio #{visit.pk} pendiente de aprobación',
                body=f'{technician.get_full_name()} — {site.name} — {scheduled_date}',
                url=reverse('manager:visit_detail', args=[visit.pk]),
                exclude_user=request.user,
            )
        messages.success(request, msg)
        return redirect(reverse('manager:visits_approval') + '?tab=planificados&q=')

    def _render(self, request, errors=None, post=None):
        from django.shortcuts import render
        return render(request, self.template_name, {
            'technicians': self._technicians(request),
            'sites':       self._sites(request),
            'errors':      errors or {},
            'post':        post or {},
        })



class VisitUpdateWebView(VisitFormMixin, PortalAccessRequiredMixin, View):
    template_name = 'manager/visit_form.html'

    def _get_visit(self, request, pk):
        qs = Visit.objects.filter(
            pk=pk,
            status=Visit.Status.PENDIENTE_APROBACION,
        ).select_related('site', 'technician')
        return get_object_or_404(qs)

    def get(self, request, pk):
        visit = self._get_visit(request, pk)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return self._render_modal(request, visit)
        return self._render(request, visit)

    def post(self, request, pk):
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
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
            if is_ajax:
                return self._render_modal(request, visit, errors=errors, post=request.POST, error_site=site, status=422)
            return self._render(request, visit, errors=errors, post=request.POST, error_site=site)

        visit.technician     = technician
        visit.site           = site
        visit.scheduled_date = scheduled_date
        visit.reason         = reason
        visit.save(update_fields=['technician', 'site', 'scheduled_date', 'reason'])
        messages.success(request, 'Servicio actualizado.')
        if is_ajax:
            return JsonResponse({'ok': True})
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

    def _render_modal(self, request, visit, errors=None, post=None, error_site=None, status=200):
        from django.shortcuts import render
        initial_site = error_site if post else visit.site
        return render(request, 'manager/partials/visit_edit_form_modal.html', {
            'technicians':  self._technicians(request),
            'errors':       errors or {},
            'post':         post or {
                'technician':     str(visit.technician_id),
                'site':           str(visit.site_id),
                'scheduled_date': str(visit.scheduled_date),
                'reason':         visit.reason,
            },
            'initial_site': initial_site,
        }, status=status)


class VisitDeleteView(SuperManagerRequiredMixin, VisitsBaseQuerysetMixin, View):
    def post(self, request, pk):
        visit = get_object_or_404(
            self.base_visit_queryset().filter(
                status__in=[Visit.Status.CANCELADA, Visit.Status.RECHAZADA]
            ),
            pk=pk,
        )
        visit.delete()
        messages.success(request, f'Servicio #{pk} eliminado.')
        return redirect(reverse('manager:visits_approval') + '?tab=cancelados')


class VisitCancelView(PortalAccessRequiredMixin, VisitsBaseQuerysetMixin, View):
    _TERMINAL = {Visit.Status.COMPLETADA, Visit.Status.CANCELADA, Visit.Status.RECHAZADA}

    def post(self, request, pk):
        reason = (request.POST.get('cancellation_reason') or '').strip()
        if not reason:
            messages.error(request, 'Debes indicar un motivo de cancelación.')
            return redirect(reverse('manager:visits_approval') + '?tab=cancelados')

        qs = self.base_visit_queryset().exclude(status__in=self._TERMINAL)
        visit = get_object_or_404(qs, pk=pk)

        visit.status_before_cancellation = visit.status
        visit.status                     = Visit.Status.CANCELADA
        visit.cancelled_by               = request.user
        visit.cancelled_at               = timezone.now()
        visit.cancellation_reason        = reason
        visit.save(update_fields=[
            'status', 'status_before_cancellation',
            'cancelled_by', 'cancelled_at', 'cancellation_reason',
        ])
        messages.success(request, f'Servicio #{pk} cancelado.')
        return redirect(reverse('manager:visits_approval') + '?tab=cancelados')


class VisitApproveView(SuperManagerRequiredMixin, VisitsBaseQuerysetMixin, View):
    def post(self, request, pk):
        visit = get_object_or_404(self.base_visit_queryset(), pk=pk)
        if visit.status != Visit.Status.PENDIENTE_APROBACION:
            messages.warning(request, 'El servicio ya no está pendiente de aprobación.')
            return redirect('manager:visit_detail', pk=pk)

        visit.status      = Visit.Status.PROGRAMADA
        visit.approved_by = request.user
        visit.approved_at = timezone.now()
        visit.save(update_fields=['status', 'approved_by', 'approved_at'])
        messages.success(request, f'Servicio #{pk} aprobado. Técnico programado.')
        return redirect(reverse('manager:visits_approval') + '?tab=planificados')


class VisitRejectView(SuperManagerRequiredMixin, VisitsBaseQuerysetMixin, View):
    def post(self, request, pk):
        reason = (request.POST.get('rejection_reason') or '').strip()
        if not reason:
            messages.error(request, 'Debes indicar un motivo de rechazo.')
            return redirect(reverse('manager:visits_approval') + '?tab=planificados')

        visit = get_object_or_404(self.base_visit_queryset(), pk=pk)
        if visit.status != Visit.Status.PENDIENTE_APROBACION:
            messages.warning(request, 'El servicio ya no está pendiente de aprobación.')
            return redirect('manager:visit_detail', pk=pk)

        visit.status_before_rejection = visit.status
        visit.status                  = Visit.Status.RECHAZADA
        visit.rejected_by             = request.user
        visit.rejected_at             = timezone.now()
        visit.rejection_reason        = reason
        visit.save(update_fields=[
            'status', 'status_before_rejection',
            'rejected_by', 'rejected_at', 'rejection_reason',
        ])
        messages.success(request, 'Servicio rechazado.')
        return redirect(reverse('manager:visits_approval') + '?tab=planificados')


@method_decorator(csrf_exempt, name='dispatch')
class VisitPhotoBulkDownloadView(PortalAccessRequiredMixin, View):

    def post(self, request):
        from visits.models import VisitPhoto
        data = json.loads(request.body)
        ids  = [int(i) for i in data.get('ids', []) if str(i).isdigit()]
        if not ids:
            return JsonResponse({'success': False, 'message': 'No se seleccionaron fotos'}, status=400)

        qs = VisitPhoto.objects.filter(pk__in=ids)
        if not request.user.is_superuser:
            qs = qs.filter(visit__technician__company=request.user.company)

        buffer     = io.BytesIO()
        seen_names = {}
        with zipfile.ZipFile(buffer, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
            for photo in qs:
                try:
                    path = photo.image.path
                    if not os.path.exists(path):
                        continue
                    filename = os.path.basename(path)
                    if filename in seen_names:
                        seen_names[filename] += 1
                        name, ext = os.path.splitext(filename)
                        filename  = f'{name}_{seen_names[filename]}{ext}'
                    else:
                        seen_names[filename] = 0
                    zf.write(path, filename)
                except Exception:
                    pass

        buffer.seek(0)
        response = StreamingHttpResponse(iter([buffer.read()]), content_type='application/zip')
        date_str = __import__('datetime').date.today().isoformat()
        response['Content-Disposition'] = f'attachment; filename="fotos_{date_str}.zip"'
        return response


@method_decorator(csrf_exempt, name='dispatch')
class VisitPhotoBulkDeleteView(PortalAccessRequiredMixin, View):

    def post(self, request):
        from visits.models import VisitPhoto
        if request.user.role not in (User.Role.SUPER_MANAGER,) and not request.user.is_superuser:
            return JsonResponse({'success': False, 'message': 'Sin permiso'}, status=403)
        data = json.loads(request.body)
        ids  = [int(i) for i in data.get('ids', []) if str(i).isdigit()]
        if not ids:
            return JsonResponse({'success': False, 'message': 'No se seleccionaron fotos'}, status=400)
        qs = VisitPhoto.objects.filter(pk__in=ids)
        if not request.user.is_superuser:
            qs = qs.filter(visit__technician__company=request.user.company)
        count = qs.count()
        qs.delete()
        return JsonResponse({'success': True, 'message': f'{count} foto(s) eliminada(s)'})
