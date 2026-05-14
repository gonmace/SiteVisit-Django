"""
flush_production_demo — elimina únicamente los datos de demostración de producción.

Borra:
  - Visitas con notas que empiezan con '[DEMO]' (+ cascade: tracking points, fotos)
  - Usuarios con email terminado en '.demo'

NO toca:
  - Sites (se preservan siempre)
  - SiteSettings (configuración de empresa)
  - Cualquier usuario o visita sin marcadores .demo / [DEMO]

Uso:
    python manage.py flush_production_demo           # pide confirmación
    python manage.py flush_production_demo --force   # sin confirmación
"""
from django.core.management.base import BaseCommand

from users.models import User
from visits.models import Visit

DEMO_EMAIL_SUFFIX  = '.demo'
DEMO_VISIT_PREFIX  = '[DEMO]'


class Command(BaseCommand):
    help = 'Elimina únicamente los datos demo de producción (visitas [DEMO] y usuarios .demo).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Ejecuta sin pedir confirmación.',
        )

    def handle(self, *args, **options):
        demo_visits = Visit.objects.filter(notas__startswith=DEMO_VISIT_PREFIX)
        demo_users  = User.objects.filter(email__endswith=DEMO_EMAIL_SUFFIX)

        visits_count = demo_visits.count()
        users_count  = demo_users.count()

        if visits_count == 0 and users_count == 0:
            self.stdout.write('  No hay datos demo que eliminar.')
            return

        self.stdout.write('━━━ Flush producción demo ━━━')
        self.stdout.write(f'  Visitas demo (+ tracking/fotos): {visits_count}')
        self.stdout.write(f'  Usuarios demo:                   {users_count}')
        self.stdout.write('')

        if not options['force']:
            confirm = input('¿Continuar? Esta acción no se puede deshacer. [s/N]: ').strip().lower()
            if confirm not in ('s', 'si', 'sí', 'y', 'yes'):
                self.stdout.write('  Cancelado.')
                return

        self.stdout.write('▶ Eliminando...')

        visits_del, _ = demo_visits.delete()
        users_del,  _ = demo_users.delete()

        self.stdout.write(self.style.SUCCESS(
            f'✓ Eliminados: {visits_del} visitas · {users_del} usuarios.'
        ))
        self.stdout.write('  Sites y SiteSettings intactos.')
