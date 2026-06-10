from django.conf import settings
from django.core.cache import cache

from .models import Notification

_CACHE_TTL = 60  # segundos


def notifications_context(request):
    user = request.user
    if not user.is_authenticated:
        return {}
    from users.models import User
    if not (user.is_superuser or user.role == User.Role.SUPER_MANAGER):
        return {}
    key = f'unread_notif_{user.pk}'
    count = cache.get(key)
    if count is None:
        count = Notification.objects.filter(user=user, is_read=False).count()
        cache.set(key, count, _CACHE_TTL)
    return {
        'unread_notifications_count': count,
        'vapid_public_key': settings.VAPID_PUBLIC_KEY,
    }
