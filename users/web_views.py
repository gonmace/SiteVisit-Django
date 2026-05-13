from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import ListView
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from users.forms import CoordinatorForm, TechnicianForm
from users.models import User, UserDevice


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
            return redirect('manager:users_list')
        return super().dispatch(request, *args, **kwargs)


class UsersListView(ManagerRequiredMixin, ListView):
    template_name = 'manager/users_list.html'
    context_object_name = 'users'
    paginate_by = 50

    def get_queryset(self):
        from django.db.models import Case, IntegerField, Value, When
        qs = User.objects.filter(role=User.Role.TECHNICIAN).select_related('device', 'profile_photo', 'status_changed_by').annotate(
            status_order=Case(
                When(status=User.Status.PENDING,  then=Value(0)),
                When(status=User.Status.ACTIVE,   then=Value(1)),
                When(status=User.Status.INACTIVE, then=Value(2)),
                default=Value(3),
                output_field=IntegerField(),
            )
        ).order_by('status_order', 'first_name')
        if self.request.user.role == User.Role.MANAGER:
            qs = qs.filter(company=self.request.user.company)
        q = self.request.GET.get('q', '').strip()
        if q:
            from django.db.models import Q
            qs = qs.filter(Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(email__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = self.request.GET.get('q', '')
        ctx['is_manager'] = True
        return ctx


class TechnicianCreateView(ManagerRequiredMixin, CreateView):
    model = User
    form_class = TechnicianForm
    template_name = 'manager/technician_form.html'
    success_url = reverse_lazy('manager:users_list')

    def get_form(self, form_class=None):
        from django import forms as dforms
        form = super().get_form(form_class)
        if self.request.user.role == User.Role.MANAGER:
            form.fields['company'].widget = dforms.HiddenInput()
            form.initial['company'] = self.request.user.company
        return form

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Agregar Técnico'
        ctx['cancel_url'] = reverse_lazy('manager:users_list')
        if self.request.user.role == User.Role.MANAGER:
            ctx['locked_company'] = self.request.user.company
        return ctx

    def form_valid(self, form):
        if self.request.user.role == User.Role.MANAGER:
            form.instance.company = self.request.user.company
        return super().form_valid(form)


class TechnicianUpdateView(ManagerRequiredMixin, UpdateView):
    model = User
    form_class = TechnicianForm
    template_name = 'manager/technician_form.html'
    success_url = reverse_lazy('manager:users_list')

    def get_queryset(self):
        qs = User.objects.filter(role=User.Role.TECHNICIAN).select_related('device')
        if self.request.user.role == User.Role.MANAGER:
            qs = qs.filter(company=self.request.user.company)
        return qs

    def _manager_status_locked(self):
        """Coordinador no puede cambiar estado si el técnico aún no registró dispositivo."""
        return (
            self.request.user.role == User.Role.MANAGER
            and not hasattr(self.object, 'device')
        )

    def get_form(self, form_class=None):
        from django import forms as dforms
        form = super().get_form(form_class)
        if self.request.user.role == User.Role.MANAGER:
            form.fields['company'].widget = dforms.HiddenInput()
            if self._manager_status_locked():
                del form.fields['status']
        return form

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'Editar Técnico — {self.object.get_full_name() or self.object.email}'
        ctx['cancel_url'] = reverse_lazy('manager:users_list')
        if self.request.user.role == User.Role.MANAGER:
            ctx['locked_company'] = self.request.user.company
        if self._manager_status_locked():
            ctx['status_locked'] = True
        return ctx

    def form_valid(self, form):
        if self.request.user.role == User.Role.MANAGER:
            form.instance.company = self.request.user.company
        if 'status' in form.changed_data:
            form.instance.status_changed_by = self.request.user
            form.instance.status_changed_at = timezone.now()
            try:
                device = form.instance.device
                device.is_active = (form.instance.status == User.Status.ACTIVE)
                device.save(update_fields=['is_active'])
            except Exception:
                pass
        return super().form_valid(form)


class TechnicianDeleteView(ManagerRequiredMixin, DeleteView):
    model = User
    template_name = 'manager/technician_confirm_delete.html'
    success_url = reverse_lazy('manager:users_list')

    def get_queryset(self):
        qs = User.objects.filter(role=User.Role.TECHNICIAN)
        if self.request.user.role == User.Role.MANAGER:
            qs = qs.filter(company=self.request.user.company)
        return qs


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
                        user.username = email[:150]
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


class PendingActivationsView(ManagerRequiredMixin, ListView):
    template_name = 'manager/pending_activations.html'
    context_object_name = 'users'
    paginate_by = 30

    def get_queryset(self):
        qs = User.objects.filter(
            status=User.Status.PENDING,
            device__isnull=False,
        ).select_related('device').order_by('-device__registered_at')

        if self.request.user.role == User.Role.MANAGER:
            qs = qs.filter(company=self.request.user.company)

        return qs


class ApproveActivationView(ManagerRequiredMixin, View):
    def post(self, request, pk):
        tech = get_object_or_404(User, pk=pk, status=User.Status.PENDING)
        if request.user.role == User.Role.MANAGER and tech.company != request.user.company:
            raise PermissionDenied
        tech.status            = User.Status.ACTIVE
        tech.status_changed_by = request.user
        tech.status_changed_at = timezone.now()
        tech.save(update_fields=['status', 'status_changed_by', 'status_changed_at'])
        try:
            tech.device.is_active = True
            tech.device.save(update_fields=['is_active'])
        except UserDevice.DoesNotExist:
            pass
        return redirect('manager:pending_activations')


class RejectActivationView(ManagerRequiredMixin, View):
    def post(self, request, pk):
        tech = get_object_or_404(User, pk=pk)
        if request.user.role == User.Role.MANAGER and tech.company != request.user.company:
            raise PermissionDenied
        try:
            tech.device.delete()
        except UserDevice.DoesNotExist:
            pass
        return redirect('manager:pending_activations')


class TechnicianResetDeviceView(SuperManagerRequiredMixin, View):
    def post(self, request, pk):
        tech = get_object_or_404(User, pk=pk, role=User.Role.TECHNICIAN)
        UserDevice.objects.filter(user=tech).delete()
        tech.status            = User.Status.INACTIVE
        tech.status_changed_by = request.user
        tech.status_changed_at = timezone.now()
        tech.save(update_fields=['status', 'status_changed_by', 'status_changed_at'])
        messages.success(
            request,
            f'Dispositivo eliminado. {tech.get_full_name() or tech.email} podrá registrarse con un nuevo dispositivo.',
        )
        return redirect('manager:users_list')


class TechnicianToggleStatusView(ManagerRequiredMixin, View):
    def post(self, request, pk):
        qs = User.objects.filter(role=User.Role.TECHNICIAN).select_related('device')
        if request.user.role == User.Role.MANAGER:
            qs = qs.filter(company=request.user.company)
        tech = get_object_or_404(qs, pk=pk)

        if request.user.role == User.Role.MANAGER and not hasattr(tech, 'device'):
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
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/manager/users/'))


# ── Coordinators ─────────────────────────────────────────────────────────────

class CoordinatorsListView(SuperManagerRequiredMixin, ListView):
    template_name = 'manager/coordinators_list.html'
    context_object_name = 'coordinators'
    paginate_by = 50

    def get_queryset(self):
        from django.db.models import Case, IntegerField, Value, When
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
            from django.db.models import Q
            qs = qs.filter(Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(email__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = self.request.GET.get('q', '')
        return ctx


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


class CoordinatorUpdateView(SuperManagerRequiredMixin, UpdateView):
    model = User
    form_class = CoordinatorForm
    template_name = 'manager/coordinator_form.html'
    success_url = reverse_lazy('manager:coordinators_list')

    def get_queryset(self):
        return User.objects.filter(role=User.Role.MANAGER)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'Editar Coordinador — {self.object.get_full_name() or self.object.email}'
        ctx['cancel_url'] = reverse_lazy('manager:coordinators_list')
        return ctx

    def form_valid(self, form):
        messages.success(self.request, f'Coordinador {form.instance.get_full_name() or form.instance.email} actualizado.')
        return super().form_valid(form)


class CoordinatorDeleteView(SuperManagerRequiredMixin, DeleteView):
    model = User
    template_name = 'manager/coordinator_confirm_delete.html'
    success_url = reverse_lazy('manager:coordinators_list')

    def get_queryset(self):
        return User.objects.filter(role=User.Role.MANAGER)

    def form_valid(self, form):
        messages.success(self.request, 'Coordinador eliminado.')
        return super().form_valid(form)


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
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/manager/coordinators/'))
