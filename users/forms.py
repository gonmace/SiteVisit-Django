from django import forms
from users.models import User

_inp = 'input input-bordered input-sm w-full'
_sel = 'select select-bordered select-sm w-full'


class TechnicianForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'rut', 'cargo', 'phone', 'company', 'status']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': _inp}),
            'last_name':  forms.TextInput(attrs={'class': _inp}),
            'email':      forms.EmailInput(attrs={'class': _inp}),
            'rut':        forms.TextInput(attrs={'class': _inp}),
            'cargo':      forms.TextInput(attrs={'class': _inp}),
            'phone':      forms.TextInput(attrs={'class': _inp}),
            'company':    forms.Select(attrs={'class': _sel}),
            'status':     forms.Select(attrs={'class': _sel}),
        }
        labels = {
            'first_name': 'Nombre',
            'last_name':  'Apellido',
            'email':      'Email',
            'rut':        'RUT',
            'cargo':      'Cargo',
            'phone':      'Teléfono',
            'company':    'Empresa',
            'status':     'Estado',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            del self.fields['status']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.TECHNICIAN
        if not user.pk:
            user.username = user.email[:150]
            user.status   = User.Status.INACTIVE
            user.set_unusable_password()
        if commit:
            user.save()
        return user


class CoordinatorForm(forms.ModelForm):
    password = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={'class': _inp}, render_value=False),
        required=False,
        help_text='Dejar vacío para no cambiar la contraseña.',
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'rut', 'cargo', 'phone', 'company', 'status']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': _inp}),
            'last_name':  forms.TextInput(attrs={'class': _inp}),
            'email':      forms.EmailInput(attrs={'class': _inp}),
            'rut':        forms.TextInput(attrs={'class': _inp}),
            'cargo':      forms.TextInput(attrs={'class': _inp}),
            'phone':      forms.TextInput(attrs={'class': _inp}),
            'company':    forms.Select(attrs={'class': _sel}),
            'status':     forms.Select(attrs={'class': _sel},
                                       choices=[(User.Status.ACTIVE, 'Activo'),
                                                (User.Status.INACTIVE, 'Inactivo')]),
        }
        labels = {
            'first_name': 'Nombre',
            'last_name':  'Apellido',
            'email':      'Email',
            'rut':        'RUT',
            'cargo':      'Cargo',
            'phone':      'Teléfono',
            'company':    'Empresa',
            'status':     'Estado',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['rut'].required = False
        if not self.instance.pk:
            self.fields['password'].required = True
            self.fields['password'].help_text = ''
            del self.fields['status']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.MANAGER
        if not user.pk:
            user.username  = user.email[:150]
            user.status    = User.Status.ACTIVE
            user.is_active = True
        else:
            status = self.cleaned_data.get('status')
            if status is not None:
                user.is_active = (int(status) == User.Status.ACTIVE)
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)
        elif not user.pk:
            user.set_unusable_password()
        if commit:
            user.save()
        return user
