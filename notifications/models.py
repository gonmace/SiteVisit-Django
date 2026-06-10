from django.conf import settings
from django.db import models


class Notification(models.Model):
    """Notificación persistente para la campana del portal (super_managers)."""

    class Event(models.TextChoices):
        VISIT_PENDING = 'visit_pending', 'Servicio pendiente de aprobación'
        TECHNICIAN_PENDING = 'technician_pending', 'Técnico pendiente de aprobación'

    user       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                   related_name='notifications')
    event      = models.CharField(max_length=30, choices=Event.choices)
    title      = models.CharField(max_length=120)
    body       = models.CharField(max_length=255, blank=True)
    url        = models.CharField(max_length=255, blank=True)  # path relativo, ej. /manager/visits/5/
    is_read    = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f'{self.get_event_display()} → {self.user}'


class PushSubscription(models.Model):
    """Suscripción Web Push (un registro por navegador/dispositivo)."""

    user       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                   related_name='push_subscriptions')
    # Los endpoints de FCM/APNs superan los 255 caracteres.
    endpoint   = models.TextField(unique=True)
    p256dh     = models.CharField(max_length=255)
    auth       = models.CharField(max_length=255)
    user_agent = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Push de {self.user} ({self.user_agent[:40]})'
