from django.db import models


class AppRelease(models.Model):
    apk         = models.FileField(upload_to='releases/', help_text='Archivo APK de la app Android')
    version     = models.CharField(max_length=20, blank=True, help_text='Ej: 1.2.3')
    notes       = models.TextField(blank=True, help_text='Notas de la versión (opcional)')
    uploaded_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'release de app'
        verbose_name_plural = 'releases de app'
        ordering            = ['-uploaded_at']

    def __str__(self):
        return f'v{self.version}' if self.version else f'Release {self.uploaded_at.date()}'


class SiteSetting(models.Model):
    """Empresa configurable desde el admin. Fuente única de verdad para
    nombre + paleta. Sustituye los overrides hardcodeados (#E6007E para wom)."""

    slug      = models.SlugField(max_length=16, unique=True,
                                 help_text='Identificador interno (wom, pti, ...)')
    name      = models.CharField(max_length=64,
                                 help_text='Nombre visible de la empresa')
    primary   = models.CharField(max_length=7, default='#F15A22',
                                 help_text='Color primario hex (#RRGGBB)')
    secondary = models.CharField(max_length=7, blank=True, default='',
                                 help_text='(opcional) Color secundario hex')
    accent    = models.CharField(max_length=7, blank=True, default='',
                                 help_text='(opcional) Color de acento hex')
    logo_url  = models.URLField(blank=True,
                                help_text='(opcional) URL del logo SVG/PNG')

    class Meta:
        verbose_name = 'empresa'
        verbose_name_plural = 'empresas'
        ordering = ['name']

    def __str__(self):
        return self.name or self.slug

    def to_dict(self):
        return {
            'name':      self.name,
            'primary':   self.primary,
            'secondary': self.secondary or self.primary,
            'accent':    self.accent    or self.primary,
            'logo_url':  self.logo_url,
        }
