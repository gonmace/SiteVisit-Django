"""Servicio central de notificaciones para super_managers y superusers.

Crea registros Notification (campana del portal) y envía Web Push a las
suscripciones de cada destinatario. El envío push corre en un thread daemon
para no bloquear la request; ningún fallo aquí debe romper la vista llamante.
"""
import json
import logging
import threading

from django.conf import settings
from django.db.models import Q

from .models import Notification, PushSubscription

logger = logging.getLogger(__name__)


def notify_supervisors(*, event, title, body='', url='', exclude_user=None):
    """Notifica a todos los super_managers activos y superusers.

    Nunca lanza excepción: los errores se registran en el log.
    """
    try:
        from users.models import User

        recipients = User.objects.filter(is_active=True).filter(
            Q(role=User.Role.SUPER_MANAGER) | Q(is_superuser=True)
        ).distinct()
        if exclude_user is not None and exclude_user.pk:
            recipients = recipients.exclude(pk=exclude_user.pk)

        recipients = list(recipients)
        if not recipients:
            return

        Notification.objects.bulk_create([
            Notification(user=u, event=event, title=title, body=body, url=url)
            for u in recipients
        ])
        _invalidate_unread_cache(recipients)

        subs = list(PushSubscription.objects.filter(user__in=recipients))
        if subs:
            threading.Thread(
                target=_send_push_batch,
                args=(subs, title, body, url),
                daemon=True,
            ).start()
    except Exception:
        logger.exception('notify_supervisors falló (evento %s)', event)


def _invalidate_unread_cache(users):
    from django.core.cache import cache
    cache.delete_many([f'unread_notif_{u.pk}' for u in users])


def _send_push_batch(subs, title, body, url):
    payload = json.dumps({'title': title, 'body': body, 'url': url})
    try:
        for sub in subs:
            _send_one(sub, payload)
    finally:
        # El thread abre su propia conexión a BD; cerrarla al terminar.
        from django.db import connection
        connection.close()


def _send_one(sub, payload):
    from pywebpush import webpush, WebPushException

    if not settings.VAPID_PRIVATE_KEY:
        logger.warning('VAPID_PRIVATE_KEY no configurada; push omitido')
        return
    try:
        webpush(
            subscription_info={
                'endpoint': sub.endpoint,
                'keys': {'p256dh': sub.p256dh, 'auth': sub.auth},
            },
            data=payload,
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            # pywebpush muta este dict: construir uno nuevo en cada llamada.
            vapid_claims={'sub': f'mailto:{settings.VAPID_ADMIN_EMAIL}'},
        )
    except WebPushException as exc:
        status = getattr(exc.response, 'status_code', None)
        if status in (404, 410):
            # Suscripción muerta (navegador la revocó): limpiar.
            PushSubscription.objects.filter(pk=sub.pk).delete()
        else:
            logger.warning('Push fallido (HTTP %s) endpoint=%s…: %s',
                           status, sub.endpoint[:60], exc)
    except Exception:
        logger.exception('Error inesperado enviando push')
