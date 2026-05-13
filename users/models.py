from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        TECHNICIAN    = 'technician',    'Technician'
        MANAGER       = 'manager',       'Coordinador'
        SUPER_MANAGER = 'super_manager', 'Manager'
        VIEWER        = 'viewer',        'Vista'

    class Company(models.TextChoices):
        WOM = 'wom', 'WOM'
        PTI = 'pti', 'PTI'

    class Status(models.IntegerChoices):
        INACTIVE = 0, 'Inactivo'
        PENDING  = 1, 'Pendiente'
        ACTIVE   = 2, 'Activo'

    email   = models.EmailField(unique=True)
    role    = models.CharField(max_length=16, choices=Role.choices, default=Role.TECHNICIAN)
    company = models.CharField(max_length=8, choices=Company.choices, blank=True)
    rut     = models.CharField(max_length=20, unique=True, blank=True, null=True, default=None)
    cargo   = models.CharField(max_length=64, blank=True)
    phone   = models.CharField(max_length=20, blank=True)
    status             = models.IntegerField(choices=Status.choices, default=Status.INACTIVE)
    status_changed_by  = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='+',
    )
    status_changed_at  = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = 'usuario'
        verbose_name_plural = 'usuarios'

    def save(self, *args, **kwargs):
        # Superusers/staff manage their own is_active; only sync for regular users
        if not self.is_superuser and not self.is_staff:
            self.is_active = (self.status != User.Status.INACTIVE)
        update_fields = kwargs.get('update_fields')
        if update_fields is not None:
            fields = list(update_fields)
            if 'status' in fields and 'is_active' not in fields:
                fields.append('is_active')
            kwargs['update_fields'] = fields
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email


class UserDevice(models.Model):
    user          = models.OneToOneField(User, on_delete=models.CASCADE, related_name='device')
    fingerprint   = models.CharField(max_length=64)
    android_id    = models.CharField(max_length=64, blank=True)
    manufacturer  = models.CharField(max_length=64, blank=True)
    model         = models.CharField(max_length=64, blank=True)
    os_version    = models.CharField(max_length=20, blank=True)
    registered_at = models.DateTimeField(auto_now_add=True)
    is_active     = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'dispositivo'
        verbose_name_plural = 'dispositivos'

    def __str__(self):
        return f'{self.user.email} — {self.model}'


class ProfilePhoto(models.Model):
    user        = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile_photo')
    image       = models.ImageField(upload_to='profile_photos/')
    taken_at    = models.DateTimeField(null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'foto de perfil'
        verbose_name_plural = 'fotos de perfil'

    def __str__(self):
        return f'Foto de {self.user.email}'
