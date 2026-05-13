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
