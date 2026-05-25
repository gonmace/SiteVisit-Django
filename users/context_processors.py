from django.core.cache import cache

_CACHE_KEY = 'pending_technicians_count'
_CACHE_TTL = 60  # segundos


def pending_technicians_count(request):
    if not request.user.is_authenticated:
        return {}
    from users.models import User
    if request.user.role not in (User.Role.MANAGER, User.Role.SUPER_MANAGER) and not request.user.is_superuser:
        return {}
    count = cache.get(_CACHE_KEY)
    if count is None:
        count = User.objects.filter(role=User.Role.TECHNICIAN, status=User.Status.PENDING).count()
        cache.set(_CACHE_KEY, count, _CACHE_TTL)
    return {'pending_technicians_count': count}
