import os

from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import Photo


@receiver(post_delete, sender=Photo)
def delete_photo_files(sender, instance, **kwargs):
    for field in (instance.imagen, instance.thumbnail):
        if field:
            try:
                if os.path.isfile(field.path):
                    os.remove(field.path)
            except Exception:
                pass
