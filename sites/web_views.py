import json

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import DetailView, ListView
from django.views.generic.edit import CreateView, DeleteView, UpdateView

from sites.forms import SiteForm
from sites.models import Site
from users.models import User


class ManagerRequiredMixin(LoginRequiredMixin):
    login_url = '/manager/login/'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if request.user.role not in (User.Role.MANAGER, User.Role.SUPER_MANAGER):
            return redirect(self.login_url)
        return super().dispatch(request, *args, **kwargs)


class SuperManagerRequiredMixin(LoginRequiredMixin):
    login_url = '/manager/login/'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if request.user.role != User.Role.SUPER_MANAGER:
            return redirect('manager:sites_list')
        return super().dispatch(request, *args, **kwargs)


class SitesListView(ManagerRequiredMixin, ListView):
    template_name = 'manager/sites_list.html'
    context_object_name = 'sites'
    paginate_by = 50

    def get_queryset(self):
        from django.db.models import Case, IntegerField, Value, When
        qs = Site.objects.annotate(
            sin_empresa=Case(
                When(company='', then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            )
        ).order_by('sin_empresa', 'code')
        if self.request.user.role == User.Role.MANAGER:
            qs = qs.filter(company=self.request.user.company)
        q = self.request.GET.get('q', '').strip()
        if q:
            from django.db.models import Q
            qs = qs.filter(Q(code__icontains=q) | Q(operator_code__icontains=q) | Q(name__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = self.request.GET.get('q', '')
        ctx['is_manager'] = self.request.user.role == User.Role.SUPER_MANAGER
        return ctx


class SiteDetailView(ManagerRequiredMixin, DetailView):
    model = Site
    template_name = 'manager/site_detail.html'
    context_object_name = 'site'

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.role == User.Role.MANAGER:
            qs = qs.filter(company=self.request.user.company)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['is_manager'] = self.request.user.role == User.Role.SUPER_MANAGER
        return ctx


class SiteCreateView(SuperManagerRequiredMixin, CreateView):
    model = Site
    form_class = SiteForm
    template_name = 'manager/site_form.html'
    success_url = reverse_lazy('manager:sites_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Agregar Sitio'
        ctx['cancel_url'] = reverse_lazy('manager:sites_list')
        return ctx


class SiteUpdateView(SuperManagerRequiredMixin, UpdateView):
    model = Site
    form_class = SiteForm
    template_name = 'manager/site_form.html'
    success_url = reverse_lazy('manager:sites_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'Editar Sitio — {self.object.code}'
        ctx['cancel_url'] = reverse_lazy('manager:sites_list')
        return ctx


class SiteDeleteView(SuperManagerRequiredMixin, DeleteView):
    model = Site
    template_name = 'manager/site_confirm_delete.html'
    success_url = reverse_lazy('manager:sites_list')


class SiteSearchJsonView(ManagerRequiredMixin, View):
    """Returns JSON list of sites matching ?q= for autocomplete in visit form."""
    def get(self, request):
        from django.db.models import Q
        q = request.GET.get('q', '').strip()
        if len(q) < 3:
            return JsonResponse([], safe=False)
        qs = Site.objects.order_by('code')
        if request.user.role == User.Role.MANAGER:
            qs = qs.filter(company=request.user.company)
        qs = qs.filter(Q(code__icontains=q) | Q(operator_code__icontains=q) | Q(name__icontains=q))
        data = [{'id': s.pk, 'code': s.code, 'operator_code': s.operator_code, 'name': s.name} for s in qs[:20]]
        return JsonResponse(data, safe=False)


class SiteImportView(SuperManagerRequiredMixin, View):
    template_name = 'manager/site_import.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        file = request.FILES.get('file')
        if not file:
            messages.error(request, 'Selecciona un archivo Excel.')
            return redirect('manager:site_import')

        try:
            import openpyxl
            wb = openpyxl.load_workbook(file, data_only=True)
            ws = wb.active

            created = updated = 0
            errors = []

            for i, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
                if not any(row):
                    continue
                try:
                    code        = str(row[0]).strip() if row[0] else ''
                    op_code     = str(row[1]).strip() if len(row) > 1 and row[1] else ''
                    name        = str(row[2]).strip() if len(row) > 2 and row[2] else ''
                    latitude    = float(row[3]) if len(row) > 3 and row[3] is not None else None
                    longitude   = float(row[4]) if len(row) > 4 and row[4] is not None else None
                    height      = int(row[5]) if len(row) > 5 and row[5] is not None else None

                    if not code or not name or latitude is None or longitude is None:
                        errors.append(f'Fila {i}: código, nombre, latitud y longitud son requeridos.')
                        continue

                    _, flag = Site.objects.update_or_create(
                        code=code,
                        defaults={
                            'operator_code': op_code,
                            'name': name,
                            'latitude': latitude,
                            'longitude': longitude,
                            'height': height,
                        },
                    )
                    if flag:
                        created += 1
                    else:
                        updated += 1

                except Exception as e:
                    errors.append(f'Fila {i}: {e}')

            msg = f'Importación completada: {created} creados, {updated} actualizados.'
            if errors:
                for err in errors[:5]:
                    messages.warning(request, err)
            messages.success(request, msg)

        except Exception as e:
            messages.error(request, f'Error al leer el archivo: {e}')

        return redirect('manager:sites_list')
