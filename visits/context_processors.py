from visits.models import Visit


def pending_visits_count(request):
    if not request.user.is_authenticated:
        return {}
    from users.models import User
    if request.user.role != User.Role.SUPER_MANAGER:
        return {}
    count = Visit.objects.filter(status=Visit.Status.PENDIENTE_APROBACION).count()
    return {'pending_visits_count': count if count else 0}
