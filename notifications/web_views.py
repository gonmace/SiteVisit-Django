"""Vistas JSON de la campana de notificaciones (portal /manager/).

Solo super_managers y superusers (SuperManagerRequiredMixin). Sesión + CSRF.
"""
import json

from django.core.cache import cache
from django.http import JsonResponse
from django.views import View

from core.mixins import SuperManagerRequiredMixin

from .models import Notification, PushSubscription


def _invalidate(user):
    cache.delete(f'unread_notif_{user.pk}')


class NotificationListView(SuperManagerRequiredMixin, View):
    """GET → últimas 20 notificaciones + contador de no leídas."""

    def get(self, request):
        qs = Notification.objects.filter(user=request.user)
        items = [{
            'id': n.pk,
            'event': n.event,
            'title': n.title,
            'body': n.body,
            'url': n.url,
            'is_read': n.is_read,
            'created_at': n.created_at.isoformat(),
        } for n in qs[:20]]
        unread = qs.filter(is_read=False).count()
        return JsonResponse({'unread_count': unread, 'items': items})


class NotificationUnreadCountView(SuperManagerRequiredMixin, View):
    """GET → solo el contador (polling ligero)."""

    def get(self, request):
        key = f'unread_notif_{request.user.pk}'
        count = cache.get(key)
        if count is None:
            count = Notification.objects.filter(user=request.user, is_read=False).count()
            cache.set(key, count, 60)
        return JsonResponse({'unread_count': count})


class NotificationMarkReadView(SuperManagerRequiredMixin, View):
    def post(self, request, pk):
        Notification.objects.filter(pk=pk, user=request.user).update(is_read=True)
        _invalidate(request.user)
        return JsonResponse({'ok': True})


class NotificationMarkAllReadView(SuperManagerRequiredMixin, View):
    def post(self, request):
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        _invalidate(request.user)
        return JsonResponse({'ok': True})


class PushSubscribeView(SuperManagerRequiredMixin, View):
    """POST {endpoint, keys: {p256dh, auth}} → guarda/actualiza la suscripción."""

    def post(self, request):
        try:
            data = json.loads(request.body)
            endpoint = data['endpoint']
            keys = data['keys']
            p256dh, auth = keys['p256dh'], keys['auth']
        except (json.JSONDecodeError, KeyError, TypeError):
            return JsonResponse({'error': 'invalid_subscription'}, status=400)

        PushSubscription.objects.update_or_create(
            endpoint=endpoint,
            defaults={
                'user': request.user,
                'p256dh': p256dh,
                'auth': auth,
                'user_agent': request.META.get('HTTP_USER_AGENT', '')[:255],
            },
        )
        return JsonResponse({'ok': True})


class PushUnsubscribeView(SuperManagerRequiredMixin, View):
    """POST {endpoint} → elimina la suscripción de este navegador."""

    def post(self, request):
        try:
            data = json.loads(request.body)
            endpoint = data['endpoint']
        except (json.JSONDecodeError, KeyError, TypeError):
            return JsonResponse({'error': 'invalid_request'}, status=400)

        PushSubscription.objects.filter(endpoint=endpoint, user=request.user).delete()
        return JsonResponse({'ok': True})
