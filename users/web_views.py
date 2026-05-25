from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import ListView
from django.views.generic.edit import CreateView, DeleteView

from django.db.models import Case, IntegerField, Q, Value, When

from core.mixins import (
    PortalAccessRequiredMixin, SuperManagerRequiredMixin, SuperuserOnlyMixin,
    CompanyScopedQuerysetMixin,
)
from users.forms import CoordinatorForm, ManagerAdminForm, TechnicianForm
from users.models import User, UserDevice


class UsersListView(PortalAccessRequiredMixin, CompanyScopedQuerysetMixin, ListView):
    template_name = 'manager/users_list.html'
    context_object_name = 'users'
    paginate_by = 50

    def get_queryset(self):
        qs = User.objects.filter(role=User.Role.TECHNICIAN).select_related('device', 'profile_photo', 'status_changed_by').annotate(
            status_order=Case(
                When(status=User.Status.PENDING,  then=Value(0)),
                When(status=User.Status.ACTIVE,   then=Value(1)),
                When(status=User.Status.INACTIVE, then=Value(2)),
                default=Value(3),
                output_field=IntegerField(),
            )
        ).order_by('status_order', 'last_name', 'first_name')
        qs = self.apply_company_filter(qs, 'company')
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(email__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        from django import forms as dforms
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = self.request.GET.get('q', '')
        ctx['is_manager'] = True
        ctx.update(self.company_context())
        all_qs = self.apply_company_filter(
            User.objects.filter(role=User.Role.TECHNICIAN), 'company'
        )
        ctx['count_active']   = all_qs.filter(status=User.Status.ACTIVE).count()
        ctx['count_inactive'] = all_qs.filter(status=User.Status.INACTIVE).count()
        ctx['count_pending']  = all_qs.filter(status=User.Status.PENDING).count()
        for user in ctx['users']:
            form = TechnicianForm(instance=user)
            if 'status' in form.fields and not hasattr(user, 'device'):
                del form.fields['status']
            user.edit_form = form
        return ctx

    def render_to_response(self, context, **response_kwargs):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return render(self.request, 'manager/partials/users_results.html', context)
        return super().render_to_response(context, **response_kwargs)


class TechnicianCreateView(PortalAccessRequiredMixin, CreateView):
    model = User
    form_class = TechnicianForm
    template_name = 'manager/technician_form.html'
    success_url = reverse_lazy('manager:users_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Agregar Técnico'
        ctx['cancel_url'] = reverse_lazy('manager:users_list')
        return ctx


class TechnicianUpdateView(PortalAccessRequiredMixin, View):
    def _get_tech(self, request, pk):
        qs = User.objects.filter(role=User.Role.TECHNICIAN).select_related('device')
        return get_object_or_404(qs, pk=pk)

    def _build_form(self, request, tech, data=None):
        form = TechnicianForm(data, instance=tech)
        if 'status' in form.fields and not hasattr(tech, 'device'):
            del form.fields['status']
        return form

    def _ctx(self, request, tech, form):
        return {
            'form': form, 'tech': tech,
            'locked_company': None,
            'status_locked': not hasattr(tech, 'device'),
        }

    def get(self, request, pk, **kwargs):
        tech = self._get_tech(request, pk)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            form = self._build_form(request, tech)
            return render(request, 'manager/technician_form_modal.html', self._ctx(request, tech, form))
        return redirect('manager:users_list')

    def post(self, request, pk, **kwargs):
        tech = self._get_tech(request, pk)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            form = self._build_form(request, tech, request.POST)
            if form.is_valid():
                if 'status' in form.changed_data:
                    form.instance.status_changed_by = request.user
                    form.instance.status_changed_at = timezone.now()
                    try:
                        tech.device.is_active = (form.instance.status == User.Status.ACTIVE)
                        tech.device.save(update_fields=['is_active'])
                    except Exception:
                        pass
                form.save()
                messages.success(request, f'Técnico {tech.get_full_name() or tech.email} actualizado.')
                return JsonResponse({'ok': True})
            return render(request, 'manager/technician_form_modal.html', self._ctx(request, tech, form), status=422)
        return redirect('manager:users_list')


class TechnicianDeleteView(PortalAccessRequiredMixin, DeleteView):
    model = User
    template_name = 'manager/technician_confirm_delete.html'
    success_url = reverse_lazy('manager:users_list')

    def get_queryset(self):
        return User.objects.filter(role=User.Role.TECHNICIAN)

    def form_valid(self, form):
        name = self.object.get_full_name() or self.object.email
        self.object.delete()
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'ok': True, 'message': f'Técnico {name} eliminado.'})
        messages.success(self.request, f'Técnico {name} eliminado.')
        return redirect(self.success_url)


class TechnicianImportView(SuperManagerRequiredMixin, View):
    template_name = 'manager/technician_import.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        file = request.FILES.get('file')
        if not file:
            messages.error(request, 'Selecciona un archivo Excel.')
            return redirect('manager:technician_import')

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
                    first_name = str(row[0]).strip() if row[0] else ''
                    last_name  = str(row[1]).strip() if len(row) > 1 and row[1] else ''
                    email      = str(row[2]).strip() if len(row) > 2 and row[2] else ''
                    rut        = str(row[3]).strip() if len(row) > 3 and row[3] else None
                    cargo      = str(row[4]).strip() if len(row) > 4 and row[4] else ''
                    phone      = str(row[5]).strip() if len(row) > 5 and row[5] else ''
                    company    = str(row[6]).strip().lower() if len(row) > 6 and row[6] else ''

                    if not first_name or not email or not company:
                        errors.append(f'Fila {i}: nombre, email y empresa son requeridos.')
                        continue

                    if company not in [c[0] for c in User.Company.choices]:
                        errors.append(f'Fila {i}: empresa "{company}" no válida (wom, pti).')
                        continue

                    user, flag = User.objects.update_or_create(
                        email=email,
                        defaults={
                            'first_name': first_name,
                            'last_name':  last_name,
                            'rut':        rut or None,
                            'cargo':      cargo,
                            'phone':      phone,
                            'company':    company,
                            'role':       User.Role.TECHNICIAN,
                            'status':     User.Status.INACTIVE,
                        },
                    )
                    if flag:
                        user.username = User.username_from_email(email)
                        user.set_unusable_password()
                        user.save(update_fields=['username', 'password'])
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

        return redirect('manager:users_list')


class PendingActivationsView(PortalAccessRequiredMixin, CompanyScopedQuerysetMixin, ListView):
    template_name = 'manager/pending_activations.html'
    context_object_name = 'users'
    paginate_by = 30

    def get_queryset(self):
        qs = User.objects.filter(
            status=User.Status.PENDING,
            device__isnull=False,
        ).select_related('device').order_by('-device__registered_at')
        return self.apply_company_filter(qs, 'company')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(self.company_context())
        return ctx


class ApproveActivationView(PortalAccessRequiredMixin, View):
    def post(self, request, pk):
        tech = get_object_or_404(User, pk=pk, status=User.Status.PENDING)
        tech.status            = User.Status.ACTIVE
        tech.status_changed_by = request.user
        tech.status_changed_at = timezone.now()
        tech.save(update_fields=['status', 'status_changed_by', 'status_changed_at'])
        try:
            tech.device.is_active = True
            tech.device.save(update_fields=['is_active'])
        except UserDevice.DoesNotExist:
            pass
        cache.delete('pending_technicians_count')
        return redirect('manager:pending_activations')


class RejectActivationView(PortalAccessRequiredMixin, View):
    def post(self, request, pk):
        tech = get_object_or_404(User, pk=pk)
        try:
            tech.device.delete()
        except UserDevice.DoesNotExist:
            pass
        cache.delete('pending_technicians_count')
        return redirect('manager:pending_activations')


class TechnicianResetDeviceView(SuperManagerRequiredMixin, View):
    def post(self, request, pk):
        tech = get_object_or_404(User, pk=pk, role=User.Role.TECHNICIAN)
        UserDevice.objects.filter(user=tech).delete()
        tech.status            = User.Status.INACTIVE
        tech.status_changed_by = request.user
        tech.status_changed_at = timezone.now()
        tech.save(update_fields=['status', 'status_changed_by', 'status_changed_at'])
        name = tech.get_full_name() or tech.email
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'ok': True, 'message': f'Dispositivo de {name} eliminado. Podrá registrarse con un nuevo celular.'})
        messages.success(request, f'Dispositivo eliminado. {name} podrá registrarse con un nuevo dispositivo.')
        return redirect('manager:users_list')


class TechnicianToggleStatusView(PortalAccessRequiredMixin, View):
    def post(self, request, pk):
        qs = User.objects.filter(role=User.Role.TECHNICIAN).select_related('device')
        tech = get_object_or_404(qs, pk=pk)

        if not hasattr(tech, 'device'):
            messages.error(request, 'No es posible cambiar el estado hasta que el técnico registre su dispositivo.')
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/manager/users/'))

        status_val = request.POST.get('status', '')
        if status_val == 'active':
            tech.status = User.Status.ACTIVE
        elif status_val == 'pending':
            tech.status = User.Status.PENDING
        elif status_val == 'inactive':
            tech.status = User.Status.INACTIVE
        tech.status_changed_by = request.user
        tech.status_changed_at = timezone.now()
        tech.save(update_fields=['status', 'status_changed_by', 'status_changed_at'])
        if hasattr(tech, 'device'):
            tech.device.is_active = (tech.status == User.Status.ACTIVE)
            tech.device.save(update_fields=['is_active'])
        nombre = tech.get_full_name() or tech.email
        cache.delete('pending_technicians_count')
        if tech.status == User.Status.ACTIVE:
            messages.success(request, f'{nombre} marcado como Activo.')
        elif tech.status == User.Status.PENDING:
            messages.warning(request, f'{nombre} marcado como Pendiente.')
        else:
            messages.warning(request, f'{nombre} marcado como Inactivo.')
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/manager/users/'))


# ── Managers (super_manager, solo superusuario) ───────────────────────────────

class ManagersListView(SuperuserOnlyMixin, ListView):
    template_name = 'manager/managers_list.html'
    context_object_name = 'managers'
    paginate_by = 50

    def get_queryset(self):
        qs = User.objects.filter(role=User.Role.SUPER_MANAGER, is_superuser=False).annotate(
            status_order=Case(
                When(status=User.Status.ACTIVE,   then=Value(0)),
                When(status=User.Status.INACTIVE, then=Value(1)),
                default=Value(2),
                output_field=IntegerField(),
            )
        ).order_by('status_order', 'first_name')
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(email__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = self.request.GET.get('q', '')
        all_qs = User.objects.filter(role=User.Role.SUPER_MANAGER, is_superuser=False)
        ctx['count_active']   = all_qs.filter(status=User.Status.ACTIVE).count()
        ctx['count_inactive'] = all_qs.filter(status=User.Status.INACTIVE).count()
        for mgr in ctx['managers']:
            mgr.edit_form = ManagerAdminForm(instance=mgr)
        return ctx

    def render_to_response(self, context, **response_kwargs):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return render(self.request, 'manager/partials/managers_results.html', context)
        return super().render_to_response(context, **response_kwargs)


class ManagerCreateView(SuperuserOnlyMixin, CreateView):
    model = User
    form_class = ManagerAdminForm
    template_name = 'manager/coordinator_form.html'
    success_url = reverse_lazy('manager:managers_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title']      = 'Agregar Manager'
        ctx['cancel_url'] = reverse_lazy('manager:managers_list')
        return ctx

    def form_valid(self, form):
        messages.success(self.request, f'Manager {form.instance.get_full_name() or form.instance.email} creado correctamente.')
        return super().form_valid(form)


class ManagerUpdateView(SuperuserOnlyMixin, View):
    def _get_mgr(self, pk):
        return get_object_or_404(User, pk=pk, role=User.Role.SUPER_MANAGER, is_superuser=False)

    def get(self, request, pk, **kwargs):
        mgr = self._get_mgr(pk)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            form = ManagerAdminForm(instance=mgr)
            return render(request, 'manager/manager_form_modal.html', {'form': form, 'mgr': mgr})
        return redirect('manager:managers_list')

    def post(self, request, pk, **kwargs):
        mgr = self._get_mgr(pk)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            form = ManagerAdminForm(request.POST, instance=mgr)
            if form.is_valid():
                form.save()
                messages.success(request, f'Manager {mgr.get_full_name() or mgr.email} actualizado.')
                return JsonResponse({'ok': True})
            return render(request, 'manager/manager_form_modal.html', {'form': form, 'mgr': mgr}, status=422)
        return redirect('manager:managers_list')


class ManagerDeleteView(SuperuserOnlyMixin, DeleteView):
    model = User
    template_name = 'manager/coordinator_confirm_delete.html'
    success_url = reverse_lazy('manager:managers_list')

    def get_queryset(self):
        return User.objects.filter(role=User.Role.SUPER_MANAGER, is_superuser=False)

    def form_valid(self, form):
        name = self.object.get_full_name() or self.object.email
        self.object.delete()
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'ok': True, 'message': f'Manager {name} eliminado.'})
        messages.success(self.request, f'Manager {name} eliminado.')
        return redirect(self.success_url)


class ManagerToggleStatusView(SuperuserOnlyMixin, View):
    def post(self, request, pk):
        mgr = get_object_or_404(User, pk=pk, role=User.Role.SUPER_MANAGER, is_superuser=False)
        status_val = request.POST.get('status', '')
        if status_val == 'active':
            mgr.status    = User.Status.ACTIVE
            mgr.is_active = True
        elif status_val == 'inactive':
            mgr.status    = User.Status.INACTIVE
            mgr.is_active = False
        mgr.save(update_fields=['status', 'is_active'])
        nombre = mgr.get_full_name() or mgr.email
        if mgr.status == User.Status.ACTIVE:
            messages.success(request, f'{nombre} marcado como Activo.')
        else:
            messages.warning(request, f'{nombre} marcado como Inactivo.')
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/manager/managers/'))


# ── Coordinators ─────────────────────────────────────────────────────────────

class CoordinatorsListView(SuperManagerRequiredMixin, ListView):
    template_name = 'manager/coordinators_list.html'
    context_object_name = 'coordinators'
    paginate_by = 50

    def get_queryset(self):
        qs = User.objects.filter(role=User.Role.MANAGER).annotate(
            status_order=Case(
                When(status=User.Status.ACTIVE,   then=Value(0)),
                When(status=User.Status.INACTIVE, then=Value(1)),
                default=Value(2),
                output_field=IntegerField(),
            )
        ).order_by('status_order', 'first_name')
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(email__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = self.request.GET.get('q', '')
        all_qs = User.objects.filter(role=User.Role.MANAGER)
        ctx['count_active']   = all_qs.filter(status=User.Status.ACTIVE).count()
        ctx['count_inactive'] = all_qs.filter(status=User.Status.INACTIVE).count()
        for coord in ctx['coordinators']:
            coord.edit_form = CoordinatorForm(instance=coord)
        return ctx

    def render_to_response(self, context, **response_kwargs):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return render(self.request, 'manager/partials/coordinators_results.html', context)
        return super().render_to_response(context, **response_kwargs)


class CoordinatorCreateView(SuperManagerRequiredMixin, CreateView):
    model = User
    form_class = CoordinatorForm
    template_name = 'manager/coordinator_form.html'
    success_url = reverse_lazy('manager:coordinators_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Agregar Coordinador'
        ctx['cancel_url'] = reverse_lazy('manager:coordinators_list')
        return ctx

    def form_valid(self, form):
        messages.success(self.request, f'Coordinador {form.instance.get_full_name() or form.instance.email} creado correctamente.')
        return super().form_valid(form)


class CoordinatorUpdateView(SuperManagerRequiredMixin, View):
    def _get_coord(self, pk):
        return get_object_or_404(User, pk=pk, role=User.Role.MANAGER)

    def get(self, request, pk, **kwargs):
        coord = self._get_coord(pk)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            form = CoordinatorForm(instance=coord)
            return render(request, 'manager/coordinator_form_modal.html', {'form': form, 'coord': coord})
        return redirect('manager:coordinators_list')

    def post(self, request, pk, **kwargs):
        coord = self._get_coord(pk)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            form = CoordinatorForm(request.POST, instance=coord)
            if form.is_valid():
                form.save()
                messages.success(request, f'Coordinador {coord.get_full_name() or coord.email} actualizado.')
                return JsonResponse({'ok': True})
            return render(request, 'manager/coordinator_form_modal.html', {'form': form, 'coord': coord}, status=422)
        return redirect('manager:coordinators_list')


class CoordinatorDeleteView(SuperManagerRequiredMixin, DeleteView):
    model = User
    template_name = 'manager/coordinator_confirm_delete.html'
    success_url = reverse_lazy('manager:coordinators_list')

    def get_queryset(self):
        return User.objects.filter(role=User.Role.MANAGER)

    def form_valid(self, form):
        name = self.object.get_full_name() or self.object.email
        self.object.delete()
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'ok': True, 'message': f'Coordinador {name} eliminado.'})
        messages.success(self.request, f'Coordinador {name} eliminado.')
        return redirect(self.success_url)


class CoordinatorToggleStatusView(SuperManagerRequiredMixin, View):
    def post(self, request, pk):
        coord = get_object_or_404(User, pk=pk, role=User.Role.MANAGER)
        status_val = request.POST.get('status', '')
        if status_val == 'active':
            coord.status    = User.Status.ACTIVE
            coord.is_active = True
        elif status_val == 'inactive':
            coord.status    = User.Status.INACTIVE
            coord.is_active = False
        coord.save(update_fields=['status', 'is_active'])
        nombre = coord.get_full_name() or coord.email
        if coord.status == User.Status.ACTIVE:
            messages.success(request, f'{nombre} marcado como Activo.')
        else:
            messages.warning(request, f'{nombre} marcado como Inactivo.')
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/manager/coordinators/'))
