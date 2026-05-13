"""
seed_demo_data — carga datos de demostración para desarrollo y pruebas.

Uso:
    python manage.py seed_demo_data           # carga sin borrar existentes
    python manage.py seed_demo_data --reset   # borra datos demo previos y recarga
"""
import random
from datetime import date, datetime, timedelta

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand
from django.utils import timezone

from sites.models import Site
from users.models import User, UserDevice
from visits.models import Visit, VisitTrackingPoint

PASSWORD = 'Test1234!'

# ── Sitios ────────────────────────────────────────────────────────────────────

SITES_WOM = [
    ('WOM-SCL001', 'RM-001', 'Las Condes Norte',       -33.4146, -70.5782, 820),
    ('WOM-SCL002', 'RM-002', 'Providencia Centro',     -33.4326, -70.6151, 560),
    ('WOM-SCL003', 'RM-003', 'Ñuñoa Sur',              -33.4575, -70.5980, 610),
    ('WOM-SCL004', 'RM-004', 'Maipú Poniente',         -33.5122, -70.7575, 490),
    ('WOM-SCL005', 'RM-005', 'Pudahuel Industrial',    -33.4378, -70.7548, 470),
    ('WOM-SCL006', 'RM-006', 'Quilicura Norte',        -33.3685, -70.7279, 510),
    ('WOM-SCL007', 'RM-007', 'Recoleta Alta',          -33.4072, -70.6526, 545),
    ('WOM-SCL008', 'RM-008', 'Peñalolén Cordillera',  -33.4809, -70.5356, 790),
    ('WOM-VAL001', 'VO-001', 'Valparaíso Cerro Alegre',-33.0472, -71.6127, 120),
    ('WOM-VAL002', 'VO-002', 'Viña del Mar Centro',   -33.0245, -71.5518,  35),
    ('WOM-CCP001', 'BI-001', 'Concepción Centro',     -36.8270, -73.0498,  20),
    ('WOM-ANT001', 'AN-001', 'Antofagasta Puerto',    -23.6509, -70.3954,  10),
]

SITES_PTI = [
    ('PTI-SCL001', 'PT-001', 'Santiago Centro Hist.',  -33.4569, -70.6483, 520),
    ('PTI-SCL002', 'PT-002', 'San Bernardo Industrial',-33.5899, -70.6446, 440),
    ('PTI-SCL003', 'PT-003', 'La Florida Sur',        -33.5168, -70.5989, 680),
    ('PTI-SCL004', 'PT-004', 'Vitacura Alto',         -33.3931, -70.5945, 710),
    ('PTI-SCL005', 'PT-005', 'Independencia Norte',   -33.4192, -70.6591, 535),
    ('PTI-SCL006', 'PT-006', 'Estación Central',      -33.4560, -70.6832, 490),
    ('PTI-SCL007', 'PT-007', 'Puente Alto',           -33.6116, -70.5758, 650),
    ('PTI-IQQ001', 'TA-001', 'Iquique Puerto',        -20.2133, -70.1503,   5),
    ('PTI-TEM001', 'AR-001', 'Temuco Centro',         -38.7359, -72.5904, 115),
    ('PTI-ARI001', 'XV-001', 'Arica Norte',           -18.4783, -70.3128,  10),
    ('PTI-COQ001', 'CO-001', 'La Serena Costa',       -29.9027, -71.2519,  25),
    ('PTI-OHI001', 'LI-001', 'Rancagua Sur',          -34.1708, -70.7444, 480),
]

# ── Técnicos adicionales (sin empresa asignada → se la damos aquí) ────────────

TECH_COMPANIES = {
    # WOM
    'carlos.munoz@test.cl':     ('wom', '12345678-9', 'Técnico RF'),
    'maria.gonzalez@test.cl':   ('wom', '13456789-0', 'Técnico Fibra'),
    'pedro.soto@test.cl':       ('wom', '14567890-1', 'Técnico RF'),
    'ana.martinez@test.cl':     ('wom', '15678901-2', 'Técnico Civil'),
    'jorge.rojas@test.cl':      ('wom', '16789012-3', 'Técnico Fibra'),
    'valentina.lopez@test.cl':  ('wom', '17890123-4', 'Técnico Civil'),
    # PTI
    'felipe.hernandez@test.cl': ('pti', '18901234-5', 'Técnico RF'),
    'camila.vargas@test.cl':    ('pti', '19012345-6', 'Técnico Fibra'),
    'diego.torres@test.cl':     ('pti', '10123456-7', 'Técnico Civil'),
    'gabriela.flores@test.cl':  ('pti', '11234567-8', 'Técnico RF'),
    'roberto.silva@test.cl':    ('pti', '12345670-K', 'Técnico Fibra'),
    'patricia.morales@test.cl': ('pti', '13456701-1', 'Técnico Civil'),
    'luis.araya@test.cl':       ('wom', '14567012-2', 'Técnico RF'),
    'carolina.fuentes@test.cl': ('wom', '15670123-3', 'Técnico Fibra'),
    'andres.pizarro@test.cl':   ('pti', '16701234-4', 'Técnico Civil'),
}

REASONS = [
    'Mantención preventiva antenas',
    'Cambio de ODU por falla reportada',
    'Ajuste de azimut y tilt',
    'Revisión de sistema de energía',
    'Instalación de nueva ODU 4G/5G',
    'Inspección post tormenta eléctrica',
    'Actualización de firmware RRU',
    'Reparación de líneas de transmisión',
    'Revisión de sistema de cooling',
    'Cambio de baterías banco de energía',
    'Instalación de equipo microonda',
    'Mantención correctiva por alarma NOC',
]


def _rnd_offset(base: float, scale: float = 0.02) -> float:
    return base + random.uniform(-scale, scale)


def _make_route(site_lat: float, site_lng: float, n_points: int = 5):
    """Genera una ruta GPS simulada llegando al sitio."""
    start_lat = site_lat + random.uniform(0.015, 0.035) * random.choice([-1, 1])
    start_lng = site_lng + random.uniform(0.015, 0.035) * random.choice([-1, 1])
    points = []
    for i in range(n_points):
        frac = i / (n_points - 1)
        lat = start_lat + (site_lat - start_lat) * frac + random.uniform(-0.0005, 0.0005)
        lng = start_lng + (site_lng - start_lng) * frac + random.uniform(-0.0005, 0.0005)
        points.append((lat, lng))
    # El último punto queda exactamente en el sitio (±5m)
    points[-1] = (site_lat + random.uniform(-0.00004, 0.00004),
                  site_lng + random.uniform(-0.00004, 0.00004))
    return points


class Command(BaseCommand):
    help = 'Carga datos de demostración (sitios, usuarios, visitas, tracking).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Elimina datos demo previos antes de cargar.',
        )

    def handle(self, *args, **options):
        random.seed(42)

        if options['reset']:
            self._flush_demo()

        self.stdout.write('━━━ Seed demo data ━━━')
        self._create_sites()
        self._update_technicians()
        self._create_visits()
        self.stdout.write(self.style.SUCCESS('\n✓ Datos de demo cargados correctamente.'))
        self.stdout.write('  Contraseña de todos los usuarios de prueba: Test1234!')

    # ── Flush ─────────────────────────────────────────────────────────────────

    def _flush_demo(self):
        self.stdout.write('▶ Eliminando datos demo previos...')
        codes = [s[0] for s in SITES_WOM + SITES_PTI]
        visits_deleted, _ = Visit.objects.filter(site__code__in=codes).delete()
        sites_deleted, _  = Site.objects.filter(code__in=codes).delete()
        emails = list(TECH_COMPANIES.keys())
        users_deleted, _  = User.objects.filter(email__in=emails).delete()
        self.stdout.write(
            f'  {visits_deleted} visitas · {sites_deleted} sitios · {users_deleted} usuarios eliminados.'
        )

    # ── Sitios ────────────────────────────────────────────────────────────────

    def _create_sites(self):
        self.stdout.write('\n▶ Sitios...')
        created = updated = 0
        for rows, company in ((SITES_WOM, 'wom'), (SITES_PTI, 'pti')):
            for code, op_code, name, lat, lng, height in rows:
                site, c = Site.objects.update_or_create(
                    code=code,
                    defaults=dict(
                        operator_code=op_code, name=name,
                        latitude=lat, longitude=lng,
                        height=height, company=company, is_active=True,
                    ),
                )
                if c:
                    created += 1
                else:
                    updated += 1
        self.stdout.write(f'  {created} creados, {updated} actualizados.')

    # ── Técnicos ──────────────────────────────────────────────────────────────

    def _update_technicians(self):
        self.stdout.write('\n▶ Técnicos...')
        updated = missing = 0
        for email, (company, rut, cargo) in TECH_COMPANIES.items():
            try:
                u = User.objects.get(email=email)
                u.company = company
                u.rut     = rut
                u.cargo   = cargo
                u.status  = User.Status.ACTIVE
                u.save(update_fields=['company', 'rut', 'cargo', 'status', 'is_active'])
                updated += 1
            except User.DoesNotExist:
                missing += 1
                self.stdout.write(f'  ! No encontrado: {email} (ejecuta create_test_users primero)')
        self.stdout.write(f'  {updated} actualizados, {missing} no encontrados.')

    # ── Visitas ───────────────────────────────────────────────────────────────

    def _create_visits(self):
        self.stdout.write('\n▶ Visitas...')

        techs_wom = list(User.objects.filter(role=User.Role.TECHNICIAN, company='wom', status=User.Status.ACTIVE))
        techs_pti = list(User.objects.filter(role=User.Role.TECHNICIAN, company='pti', status=User.Status.ACTIVE))
        sites_wom = list(Site.objects.filter(company='wom'))
        sites_pti = list(Site.objects.filter(company='pti'))

        coord_wom = User.objects.filter(role=User.Role.MANAGER, company='wom').first()
        coord_pti = User.objects.filter(role=User.Role.MANAGER, company='pti').first()
        super_mgr = User.objects.filter(role=User.Role.SUPER_MANAGER).first()

        if not techs_wom and not techs_pti:
            self.stdout.write('  ! Sin técnicos activos. Ejecuta create_test_users primero.')
            return

        today = timezone.localdate()
        created = 0

        def _tech_site(company):
            if company == 'wom':
                return random.choice(techs_wom or techs_pti), random.choice(sites_wom or sites_pti)
            return random.choice(techs_pti or techs_wom), random.choice(sites_pti or sites_wom)

        # 1. COMPLETADAS — últimos 30 días, con tracking points
        for i in range(24):
            days_ago = random.randint(1, 30)
            sched = today - timedelta(days=days_ago)
            company = 'wom' if i % 2 == 0 else 'pti'
            tech, site = _tech_site(company)
            coord = coord_wom if company == 'wom' else coord_pti

            t_start = datetime.combine(sched, datetime.min.time()).replace(
                hour=random.randint(8, 10), minute=random.randint(0, 59), tzinfo=timezone.get_current_timezone()
            )
            duration_min = random.randint(45, 180)
            t_end = t_start + timedelta(minutes=duration_min)

            v = Visit.objects.create(
                technician=tech, site=site, coordinator=coord,
                status=Visit.Status.COMPLETADA,
                reason=random.choice(REASONS),
                scheduled_date=sched,
                hora_inicio_trabajos=t_start,
                hora_fin_trabajos=t_end,
                approved_by=super_mgr, approved_at=t_start - timedelta(hours=random.randint(2, 48)),
            )
            self._add_tracking(v, site, t_start, t_end)
            created += 1

        # 2. PROGRAMADAS — próximos 14 días
        for i in range(18):
            days_ahead = random.randint(1, 14)
            sched = today + timedelta(days=days_ahead)
            company = 'wom' if i % 2 == 0 else 'pti'
            tech, site = _tech_site(company)
            coord = coord_wom if company == 'wom' else coord_pti

            Visit.objects.create(
                technician=tech, site=site, coordinator=coord,
                status=Visit.Status.PROGRAMADA,
                reason=random.choice(REASONS),
                scheduled_date=sched,
                approved_by=super_mgr, approved_at=timezone.now() - timedelta(hours=random.randint(1, 72)),
            )
            created += 1

        # 3. PENDIENTE APROBACIÓN — últimos 7 días
        for i in range(9):
            days_ago = random.randint(0, 7)
            sched = today - timedelta(days=days_ago)
            company = 'wom' if i % 2 == 0 else 'pti'
            tech, site = _tech_site(company)
            coord = coord_wom if company == 'wom' else coord_pti

            Visit.objects.create(
                technician=tech, site=site, coordinator=coord,
                status=Visit.Status.PENDIENTE_APROBACION,
                reason=random.choice(REASONS),
                scheduled_date=sched,
            )
            created += 1

        # 4. EN EJECUCIÓN — hoy (en_camino / llegada / trabajando)
        active_statuses = [Visit.Status.EN_CAMINO, Visit.Status.LLEGADA, Visit.Status.TRABAJANDO]
        for i, status in enumerate(active_statuses):
            company = 'wom' if i % 2 == 0 else 'pti'
            tech, site = _tech_site(company)
            coord = coord_wom if company == 'wom' else coord_pti

            t_start = datetime.combine(today, datetime.min.time()).replace(
                hour=random.randint(7, 9), minute=random.randint(0, 30), tzinfo=timezone.get_current_timezone()
            )
            v = Visit.objects.create(
                technician=tech, site=site, coordinator=coord,
                status=status,
                reason=random.choice(REASONS),
                scheduled_date=today,
                hora_inicio_trabajos=t_start if status in (Visit.Status.TRABAJANDO, Visit.Status.LLEGADA) else None,
                approved_by=super_mgr, approved_at=t_start - timedelta(hours=2),
            )
            # Algunos tracking points parciales
            route = _make_route(site.latitude, site.longitude, 3)
            events = ['salida', 'llegada', 'inicio']
            for j, (pt_status, (lat, lng)) in enumerate(zip(events, route)):
                if status == Visit.Status.EN_CAMINO and j > 0:
                    break
                if status == Visit.Status.LLEGADA and j > 1:
                    break
                VisitTrackingPoint.objects.create(
                    visit=v, event=pt_status, latitude=lat, longitude=lng,
                    timestamp=t_start + timedelta(minutes=j * 20),
                )
            created += 1

        # 5. CANCELADAS — últimos 30 días
        for i in range(7):
            days_ago = random.randint(1, 30)
            sched = today - timedelta(days=days_ago)
            company = 'wom' if i % 2 == 0 else 'pti'
            tech, site = _tech_site(company)
            coord = coord_wom if company == 'wom' else coord_pti

            Visit.objects.create(
                technician=tech, site=site, coordinator=coord,
                status=Visit.Status.CANCELADA,
                reason=random.choice(REASONS),
                scheduled_date=sched,
                notas='Cancelado por solicitud del área de operaciones.',
            )
            created += 1

        # 6. RECHAZADAS — últimos 20 días
        for i in range(5):
            days_ago = random.randint(1, 20)
            sched = today - timedelta(days=days_ago)
            company = 'wom' if i % 2 == 0 else 'pti'
            tech, site = _tech_site(company)
            coord = coord_wom if company == 'wom' else coord_pti

            Visit.objects.create(
                technician=tech, site=site, coordinator=coord,
                status=Visit.Status.RECHAZADA,
                reason=random.choice(REASONS),
                scheduled_date=sched,
                rejected_by=super_mgr,
                rejected_at=timezone.now() - timedelta(days=days_ago - 1),
                rejection_reason='Documentación incompleta. Reprogramar con antecedentes.',
            )
            created += 1

        self.stdout.write(f'  {created} visitas creadas.')

    # ── Tracking ──────────────────────────────────────────────────────────────

    def _add_tracking(self, visit: Visit, site: Site, t_start: datetime, t_end: datetime):
        route = _make_route(site.latitude, site.longitude)
        events = ['salida', 'llegada', 'inicio', 'finalizado', 'cierre']
        total_secs = (t_end - t_start).total_seconds()
        # salida=0%, llegada=25%, inicio=30%, finalizado=90%, cierre=100%
        offsets = [0.0, 0.25, 0.30, 0.90, 1.0]

        for event, (lat, lng), frac in zip(events, route, offsets):
            VisitTrackingPoint.objects.create(
                visit=visit,
                event=event,
                latitude=lat,
                longitude=lng,
                timestamp=t_start + timedelta(seconds=total_secs * frac),
            )
