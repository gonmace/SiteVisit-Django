from django import forms
from sites.models import Site

_inp = 'input input-bordered input-sm w-full'
_sel = 'select select-bordered select-sm w-full'


class SiteForm(forms.ModelForm):
    class Meta:
        model = Site
        fields = ['code', 'operator_code', 'name', 'latitude', 'longitude', 'height', 'company', 'is_active']
        widgets = {
            'code':          forms.TextInput(attrs={'class': _inp}),
            'operator_code': forms.TextInput(attrs={'class': _inp}),
            'name':          forms.TextInput(attrs={'class': _inp}),
            'latitude':      forms.NumberInput(attrs={'class': _inp, 'step': 'any'}),
            'longitude':     forms.NumberInput(attrs={'class': _inp, 'step': 'any'}),
            'height':        forms.NumberInput(attrs={'class': _inp}),
            'company':       forms.Select(attrs={'class': _sel}),
            'is_active':     forms.CheckboxInput(attrs={'class': 'checkbox checkbox-sm checkbox-primary'}),
        }
        labels = {
            'code':          'Código Sitio',
            'operator_code': 'Código Operador',
            'name':          'Nombre Sitio',
            'latitude':      'Latitud',
            'longitude':     'Longitud',
            'height':        'Altura (m)',
            'company':       'Empresa',
            'is_active':     'Activo',
        }
