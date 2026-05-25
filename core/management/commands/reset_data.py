"""
Elimina todos los datos operativos manteniendo usuarios, dispositivos y configuración.

Uso:
    python manage.py reset_data           # pide confirmación interactiva
    python manage.py reset_data --yes     # sin confirmación (para scripts)
"""

import os
import shutil

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = 'Elimina visitas, fotos, sitios y tracking. Conserva usuarios y configuración.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--yes', action='store_true',
            help='Omite la confirmación interactiva.',
        )

    def handle(self, *args, **options):
        if not options['yes']:
            self.stdout.write(self.style.WARNING(
                '\n¡ATENCIÓN! Se eliminarán PERMANENTEMENTE:\n'
                '  • Todas las visitas y su tracking GPS\n'
                '  • Todas las fotos de visitas\n'
                '  • Todos los sitios\n'
                '  • Todos los archivos de medios (media/)\n'
                '\nSe CONSERVARÁN:\n'
                '  • Usuarios, dispositivos y fotos de perfil\n'
                '  • Configuración de empresa (SiteSetting)\n'
                '  • Releases de la app (AppRelease)\n'
            ))
            confirm = input('Escribe "CONFIRMAR" para continuar: ')
            if confirm.strip() != 'CONFIRMAR':
                self.stdout.write(self.style.ERROR('Cancelado.'))
                return

        self.stdout.write('Eliminando datos…')

        with transaction.atomic():
            from photos.models import Photo
            from visits.models import Visit, VisitPhoto, VisitTrackingPoint

            counts = {
                'tracking': VisitTrackingPoint.objects.count(),
                'visit_photos': VisitPhoto.objects.count(),
                'photos': Photo.objects.count(),
                'visits': Visit.objects.count(),
            }

            VisitTrackingPoint.objects.all().delete()
            VisitPhoto.objects.all().delete()
            Photo.objects.all().delete()
            Visit.objects.all().delete()

            from sites.models import Site
            counts['sites'] = Site.objects.count()
            Site.objects.all().delete()

        # Limpia archivos de media (excepto releases/ y profile_photos/)
        media_root = settings.MEDIA_ROOT
        if media_root and os.path.isdir(media_root):
            preserved = {'releases', 'profile_photos'}
            for entry in os.scandir(media_root):
                if entry.name in preserved:
                    continue
                try:
                    if entry.is_dir(follow_symlinks=False):
                        shutil.rmtree(entry.path)
                    else:
                        os.remove(entry.path)
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'  No se pudo eliminar {entry.path}: {e}'))

        self.stdout.write(self.style.SUCCESS(
            f'\nListo:\n'
            f'  {counts["tracking"]:>6} puntos de tracking eliminados\n'
            f'  {counts["visit_photos"]:>6} fotos de visita eliminadas\n'
            f'  {counts["photos"]:>6} fotos genéricas eliminadas\n'
            f'  {counts["visits"]:>6} visitas eliminadas\n'
            f'  {counts["sites"]:>6} sitios eliminados\n'
            f'  Archivos de media limpiados (conservados: releases/, profile_photos/)\n'
        ))
