from django import template
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from photos.models import Photo

register = template.Library()


@register.simple_tag
def photo_upload_url(obj, etapa=''):
    """Return the upload URL for the camera widget attached to any model instance.
    Usage: {% load photo_tags %}{% photo_upload_url visit 'trabajo' %}
    """
    ct  = ContentType.objects.get_for_model(obj)
    url = reverse('manager:photos:upload', kwargs={'ct_id': ct.pk, 'object_id': obj.pk})
    return url


@register.simple_tag
def photo_count(obj, etapa=''):
    """Return the number of photos attached to a model instance.
    Usage: {% photo_count visit 'trabajo' %}
    """
    ct = ContentType.objects.get_for_model(obj)
    qs = Photo.objects.filter(content_type=ct, object_id=obj.pk)
    if etapa:
        qs = qs.filter(etapa=etapa)
    return qs.count()
