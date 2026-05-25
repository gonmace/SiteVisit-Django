import os
from io import BytesIO

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class Photo(models.Model):
    content_type  = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id     = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    app          = models.CharField(max_length=100)
    etapa        = models.CharField(max_length=255, blank=True)
    imagen       = models.ImageField(upload_to='photos/')
    thumbnail    = models.ImageField(upload_to='photos/thumbs/', null=True, blank=True)
    descripcion  = models.CharField(max_length=255, blank=True)
    orden        = models.IntegerField(default=0)

    exif_lat      = models.FloatField(null=True, blank=True)
    exif_lon      = models.FloatField(null=True, blank=True)
    exif_datetime = models.DateTimeField(null=True, blank=True)
    file_size     = models.PositiveIntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'foto'
        verbose_name_plural = 'fotos'
        ordering            = ['orden', '-created_at']

    def __str__(self):
        return f'Photo {self.pk} — {self.content_type} #{self.object_id}'

    @property
    def thumbnail_url(self):
        if self.thumbnail:
            return self.thumbnail.url
        return self.imagen.url if self.imagen else ''

    def generate_thumbnail(self, size=(400, 400)):
        if not self.imagen:
            return
        try:
            from PIL import Image, ImageOps
            orig_path  = self.imagen.path
            thumb_dir  = os.path.join(os.path.dirname(orig_path), 'thumbs')
            os.makedirs(thumb_dir, exist_ok=True)
            thumb_name = os.path.splitext(os.path.basename(orig_path))[0] + '.jpg'
            thumb_abs  = os.path.join(thumb_dir, thumb_name)

            with Image.open(orig_path) as img:
                img = ImageOps.exif_transpose(img)
                img.thumbnail(size, Image.LANCZOS)
                buf = BytesIO()
                img.convert('RGB').save(buf, format='JPEG', quality=82, optimize=True)

            with open(thumb_abs, 'wb') as f:
                f.write(buf.getvalue())

            relative = os.path.relpath(thumb_abs, settings.MEDIA_ROOT)
            Photo.objects.filter(pk=self.pk).update(thumbnail=relative)
            self.thumbnail = relative
        except Exception:
            pass

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        # Auto-set app from content_type
        if not self.app and self.content_type_id:
            try:
                ct = ContentType.objects.get(pk=self.content_type_id)
                self.app = ct.app_label
            except ContentType.DoesNotExist:
                pass
        super().save(*args, **kwargs)
        if is_new and self.imagen:
            self._populate_file_size()
            if self.exif_lat is None and self.exif_datetime is None:
                self._extract_exif()
            self.generate_thumbnail()

    def _populate_file_size(self):
        try:
            size = os.path.getsize(self.imagen.path)
            Photo.objects.filter(pk=self.pk).update(file_size=size)
            self.file_size = size
        except Exception:
            pass

    def _extract_exif(self):
        try:
            import datetime
            from PIL import Image
            from PIL.ExifTags import GPSTAGS, TAGS

            with Image.open(self.imagen.path) as img:
                exif_raw = img._getexif()
            if not exif_raw:
                return

            exif = {TAGS.get(k, k): v for k, v in exif_raw.items()}

            for tag in ('DateTimeOriginal', 'DateTimeDigitized', 'DateTime'):
                dt_str = exif.get(tag)
                if dt_str:
                    try:
                        self.exif_datetime = datetime.datetime.strptime(
                            str(dt_str).strip(), '%Y:%m:%d %H:%M:%S'
                        )
                        break
                    except ValueError:
                        pass

            gps_raw = exif.get('GPSInfo')
            if gps_raw:
                gps = {GPSTAGS.get(k, k): v for k, v in gps_raw.items()}

                def _dms(dms, ref):
                    d, m, s = (float(x) for x in dms)
                    decimal  = d + m / 60 + s / 3600
                    return -decimal if ref in ('S', 'W') else decimal

                lat_dms = gps.get('GPSLatitude')
                lat_ref = gps.get('GPSLatitudeRef')
                lon_dms = gps.get('GPSLongitude')
                lon_ref = gps.get('GPSLongitudeRef')

                if lat_dms and lat_ref and lon_dms and lon_ref:
                    self.exif_lat = _dms(lat_dms, lat_ref)
                    self.exif_lon = _dms(lon_dms, lon_ref)

            if self.exif_lat is not None or self.exif_datetime is not None:
                Photo.objects.filter(pk=self.pk).update(
                    exif_lat=self.exif_lat,
                    exif_lon=self.exif_lon,
                    exif_datetime=self.exif_datetime,
                )
        except Exception:
            pass
