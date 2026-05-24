from django.core.cache import cache

from visits.models import Visit

_CACHE_KEY = 'pending_visits_count'
_CACHE_TTL = 60  # segundos


def pending_visits_count(request):
    if not request.user.is_authenticated:
        return {}
    from users.models import User
    if request.user.role != User.Role.SUPER_MANAGER:
        return {}
    count = cache.get(_CACHE_KEY)
    if count is None:
        count = Visit.objects.filter(status=Visit.Status.PENDIENTE_APROBACION).count()
        cache.set(_CACHE_KEY, count, _CACHE_TTL)
    return {'pending_visits_count': count}
