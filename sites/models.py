from django.db import models

from users.models import User


class Site(models.Model):
    code          = models.CharField(max_length=20, unique=True)
    operator_code = models.CharField(max_length=40, blank=True)
    name          = models.CharField(max_length=128)
    latitude      = models.FloatField()
    longitude     = models.FloatField()
    height        = models.IntegerField(null=True, blank=True)
    comuna        = models.CharField(max_length=64, blank=True, default='')
    region        = models.CharField(max_length=64, blank=True, default='')
    company       = models.CharField(max_length=8, choices=User.Company.choices)
    is_active     = models.BooleanField(default=True)
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'sitio'
        verbose_name_plural = 'sitios'
        ordering = ['code']

    def __str__(self):
        return f'{self.code} — {self.name}'
