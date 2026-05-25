from django import template

register = template.Library()


@register.filter
def initials(value):
    if not value:
        return ""
    parts = value.split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    return value[:2].upper()


_STATUS_LABELS = {
    'pendiente_aprobacion': 'Pendiente',
    'programada':           'Programado',
    'en_camino':            'En camino',
    'llegada':              'Sitio',
    'trabajando':           'Servicio',
    'finalizando':          'Finalizando',
    'completada':           'Completado',
    'cancelada':            'Cancelado',
    'rechazada':            'Rechazado',
}


@register.filter
def status_display(value):
    return _STATUS_LABELS.get(value, value)
