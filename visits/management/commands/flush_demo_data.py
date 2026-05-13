"""
flush_demo_data — elimina todos los datos de demostración del sistema.

Borra:
  - Todas las visitas (cascada → fotos, tracking points)
  - Todos los sitios del catálogo demo
  - Usuarios técnicos de prueba (@test.cl)

NO toca:
  - Superusuarios / staff
  - Managers / coordinadores
  - Datos reales (si los hay)

Uso:
    python manage.py flush_demo_data           # pide confirmación
    python manage.py flush_demo_data --force   # sin confirmación (CI/scripts)
"""
from django.core.management.base import BaseCommand

from sites.models import Site
from users.models import User
from visits.models import Visit

DEMO_SITE_PREFIXES = ('WOM-', 'PTI-')
DEMO_USER_DOMAIN   = '@test.cl'


class Command(BaseCommand):
    help = 'Elimina todos los datos de demostración (visitas, sitios, técnicos de prueba).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Ejecuta sin pedir confirmación.',
        )

    def handle(self, *args, **options):
        # Contar lo que se va a borrar
        demo_sites   = Site.objects.filter(code__startswith='WOM-') | Site.objects.filter(code__startswith='PTI-')
        demo_site_ids = demo_sites.values_list('id', flat=True)
        visits_count  = Visit.objects.filter(site_id__in=demo_site_ids).count()
        sites_count   = demo_sites.count()
        techs_count   = User.objects.filter(email__endswith=DEMO_USER_DOMAIN).count()

        if visits_count == 0 and sites_count == 0 and techs_count == 0:
            self.stdout.write('  No hay datos de demo que eliminar.')
            return

        self.stdout.write('━━━ Flush demo data ━━━')
        self.stdout.write(f'  Visitas (+ fotos + tracking): {visits_count}')
        self.stdout.write(f'  Sitios:                       {sites_count}')
        self.stdout.write(f'  Técnicos de prueba:           {techs_count}')
        self.stdout.write('')

        if not options['force']:
            confirm = input('¿Continuar? Esta acción no se puede deshacer. [s/N]: ').strip().lower()
            if confirm not in ('s', 'si', 'sí', 'y', 'yes'):
                self.stdout.write('  Cancelado.')
                return

        self.stdout.write('▶ Eliminando...')

        visits_del, _ = Visit.objects.filter(site_id__in=demo_site_ids).delete()
        sites_del,  _ = demo_sites.delete()
        users_del,  _ = User.objects.filter(email__endswith=DEMO_USER_DOMAIN).delete()

        self.stdout.write(self.style.SUCCESS(
            f'✓ Eliminados: {visits_del} visitas · {sites_del} sitios · {users_del} usuarios.'
        ))
