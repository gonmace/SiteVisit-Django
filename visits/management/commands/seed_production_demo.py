"""
seed_production_demo — carga datos de demostración para producción.

Asume que los Sites YA están cargados en la BD. No toca Sites.
Usa marcadores .demo en emails y [DEMO] en notas para limpieza segura.

Uso:
    python manage.py seed_production_demo
    python manage.py seed_production_demo --password=MiPassword123
    python manage.py seed_production_demo --reset            # flush + seed
    python manage.py seed_production_demo --skip-users       # solo visitas
    python manage.py seed_production_demo --skip-visits      # solo cuentas
"""
import random
import unicodedata
from datetime import date, datetime, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from home.models import SiteSetting
from sites.models import Site
from users.models import User
from visits.models import Visit, VisitTrackingPoint

DEFAULT_PASSWORD = 'SiteVisit2026!'

# ── Cuentas admin / coordinación ──────────────────────────────────────────────

STAFF_USERS = [
    # (email, username, first_name, last_name, role, company, is_staff, is_superuser)
    ('admin@sitevisit.demo',        'admin_demo',     'Admin',       'Demo',     User.Role.SUPER_MANAGER, User.Company.WOM, True,  True),
    ('supermanager@sitevisit.demo', 'super_demo',     'Super',       'Manager',  User.Role.SUPER_MANAGER, User.Company.WOM, False, False),
    ('manager@wom.demo',            'mgr_wom_demo',   'Coordinador', 'WOM',      User.Role.MANAGER,       User.Company.WOM, False, False),
    ('manager@pti.demo',            'mgr_pti_demo',   'Coordinador', 'PTI',      User.Role.MANAGER,       User.Company.PTI, False, False),
    ('viewer@wom.demo',             'view_wom_demo',  'Visor',       'WOM',      User.Role.VIEWER,        User.Company.WOM, False, False),
    ('viewer@pti.demo',             'view_pti_demo',  'Visor',       'PTI',      User.Role.VIEWER,        User.Company.PTI, False, False),
]

# ── Técnicos demo ─────────────────────────────────────────────────────────────

TECHNICIANS_DEMO = [
    # (first_name, last_name, company, rut, cargo)
    ('Carlos',    'Munoz',     'wom', '12.345.678-9', 'Técnico RF'),
    ('Maria',     'Gonzalez',  'wom', '13.456.789-0', 'Técnico Fibra'),
    ('Pedro',     'Soto',      'wom', '14.567.890-1', 'Técnico RF'),
    ('Ana',       'Martinez',  'wom', '15.678.901-2', 'Técnico Civil'),
    ('Jorge',     'Rojas',     'wom', '16.789.012-3', 'Técnico Fibra'),
    ('Valentina', 'Lopez',     'wom', '17.890.123-4', 'Técnico Civil'),
    ('Felipe',    'Hernandez', 'pti', '18.901.234-5', 'Técnico RF'),
    ('Camila',    'Vargas',    'pti', '19.012.345-6', 'Técnico Fibra'),
    ('Diego',     'Torres',    'pti', '20.123.456-7', 'Técnico Civil'),
    ('Gabriela',  'Flores',    'pti', '21.234.567-8', 'Técnico RF'),
    ('Roberto',   'Silva',     'pti', '22.345.670-K', 'Técnico Fibra'),
    ('Patricia',  'Morales',   'pti', '23.456.701-1', 'Técnico Civil'),
]

# ── Razones de visita ─────────────────────────────────────────────────────────

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


def _ascii_slug(text: str) -> str:
    """Convierte 'González' → 'gonzalez' para emails y usernames."""
    normalized = unicodedata.normalize('NFD', text)
    ascii_only = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')
    return ascii_only.lower()


def _make_route(site_lat: float, site_lng: float, n_points: int = 5):
    """Genera una ruta GPS simulada llegando al sitio."""
    start_lat = site_lat + random.uniform(0.015, 0.035) * random.choice([-1, 1])
    start_lng = site_lng + random.uniform(0.015, 0.035) * random.choice([-1, 1])
    if n_points == 1:
        return [(start_lat, start_lng)]
    points = []
    for i in range(n_points):
        frac = i / (n_points - 1)
        lat = start_lat + (site_lat - start_lat) * frac + random.uniform(-0.0005, 0.0005)
        lng = start_lng + (site_lng - start_lng) * frac + random.uniform(-0.0005, 0.0005)
        points.append((lat, lng))
    points[-1] = (
        site_lat + random.uniform(-0.00004, 0.00004),
        site_lng + random.uniform(-0.00004, 0.00004),
    )
    return points


def _add_tracking(visit: Visit, site: Site, t_start: datetime, t_end: datetime):
    route = _make_route(site.latitude, site.longitude)
    events = ['salida', 'llegada', 'inicio', 'finalizado', 'cierre']
    total_secs = (t_end - t_start).total_seconds()
    offsets = [0.0, 0.25, 0.30, 0.90, 1.0]
    for event, (lat, lng), frac in zip(events, route, offsets):
        VisitTrackingPoint.objects.create(
            visit=visit,
            event=event,
            latitude=lat,
            longitude=lng,
            timestamp=t_start + timedelta(seconds=total_secs * frac),
        )


class Command(BaseCommand):
    help = 'Carga datos de demostración para producción (Sites ya deben existir).'

    def add_arguments(self, parser):
        parser.add_argument('--password', default=DEFAULT_PASSWORD,
                            help=f'Password para todas las cuentas demo (default: {DEFAULT_PASSWORD})')
        parser.add_argument('--reset', action='store_true',
                            help='Elimina datos demo previos antes de cargar.')
        parser.add_argument('--skip-users', action='store_true',
                            help='Omite creación de cuentas (asume que ya existen).')
        parser.add_argument('--skip-visits', action='store_true',
                            help='Omite creación de visitas.')

    def handle(self, *args, **options):
        random.seed(2026)
        password = options['password']

        # Pre-chequeo: sitios cargados
        wom_count = Site.objects.filter(company='wom', is_active=True).count()
        pti_count = Site.objects.filter(company='pti', is_active=True).count()
        if wom_count == 0:
            raise CommandError('No hay sitios activos para empresa "wom". Carga los sitios primero.')
        if pti_count == 0:
            raise CommandError('No hay sitios activos para empresa "pti". Carga los sitios primero.')

        if options['reset']:
            self._flush_demo()

        self.stdout.write('━━━ Seed producción demo ━━━')

        settings_count = self._create_site_settings()
        staff_count = tech_count = 0

        if not options['skip_users']:
            staff_count = self._create_staff(password)
            tech_count  = self._create_technicians(password)

        visits_count = 0
        if not options['skip_visits']:
            visits_count = self._create_visits()

        self._print_banner(password, settings_count, staff_count, tech_count, visits_count)

    # ── Flush interno (espejo de flush_production_demo) ───────────────────────

    def _flush_demo(self):
        self.stdout.write('▶ Eliminando datos demo previos...')
        v_del, _ = Visit.objects.filter(notas__startswith='[DEMO]').delete()
        u_del, _ = User.objects.filter(email__endswith='.demo').delete()
        self.stdout.write(f'  {v_del} visitas · {u_del} usuarios eliminados.')

    # ── SiteSettings ──────────────────────────────────────────────────────────

    def _create_site_settings(self):
        self.stdout.write('\n▶ SiteSettings...')
        configs = [
            ('wom', 'WOM', '#E6007E'),
            ('pti', 'PTI', '#F15A22'),
        ]
        count = 0
        for slug, name, primary in configs:
            _, created = SiteSetting.objects.get_or_create(
                slug=slug,
                defaults={'name': name, 'primary': primary},
            )
            label = 'creado' if created else 'ya existía'
            self.stdout.write(f'  {slug}: {label}')
            count += 1
        return count

    # ── Cuentas admin/coordinación ────────────────────────────────────────────

    def _create_staff(self, password: str) -> int:
        self.stdout.write('\n▶ Cuentas admin/coordinación...')
        count = 0
        for email, username, first_name, last_name, role, company, is_staff, is_superuser in STAFF_USERS:
            user, created = User.objects.get_or_create(
                email=email,
                defaults={'username': username, 'first_name': first_name,
                          'last_name': last_name},
            )
            user.role         = role
            user.company      = company
            user.is_staff     = is_staff
            user.is_superuser = is_superuser
            user.status       = User.Status.ACTIVE
            if is_superuser:
                user.is_active = True
            user.set_password(password)
            user.save()
            label = 'creado' if created else 'actualizado'
            self.stdout.write(f'  [{label}] {email}')
            count += 1
        return count

    # ── Técnicos demo ─────────────────────────────────────────────────────────

    def _create_technicians(self, password: str) -> int:
        self.stdout.write('\n▶ Técnicos demo...')
        count = 0
        for first_name, last_name, company, rut, cargo in TECHNICIANS_DEMO:
            first_slug = _ascii_slug(first_name)
            last_slug  = _ascii_slug(last_name)
            email      = f'{first_slug}.{last_slug}@{company}.demo'
            username   = f'{first_slug[0]}{last_slug}_d'

            user, created = User.objects.get_or_create(
                email=email,
                defaults={'username': username, 'first_name': first_name,
                          'last_name': last_name},
            )
            user.role    = User.Role.TECHNICIAN
            user.company = company
            user.rut     = rut
            user.cargo   = cargo
            user.status  = User.Status.ACTIVE
            user.set_password(password)
            user.save()
            label = 'creado' if created else 'actualizado'
            self.stdout.write(f'  [{label}] {email}')
            count += 1
        return count

    # ── Visitas ───────────────────────────────────────────────────────────────

    def _create_visits(self) -> int:
        self.stdout.write('\n▶ Visitas...')

        techs_wom = list(User.objects.filter(
            role=User.Role.TECHNICIAN, company='wom',
            status=User.Status.ACTIVE, email__endswith='.demo',
        ))
        techs_pti = list(User.objects.filter(
            role=User.Role.TECHNICIAN, company='pti',
            status=User.Status.ACTIVE, email__endswith='.demo',
        ))
        sites_wom = list(Site.objects.filter(company='wom', is_active=True))
        sites_pti = list(Site.objects.filter(company='pti', is_active=True))

        coord_wom  = User.objects.filter(role=User.Role.MANAGER, company='wom', email__endswith='.demo').first()
        coord_pti  = User.objects.filter(role=User.Role.MANAGER, company='pti', email__endswith='.demo').first()
        super_mgr  = User.objects.filter(role=User.Role.SUPER_MANAGER, email='supermanager@sitevisit.demo').first()

        if not techs_wom and not techs_pti:
            self.stdout.write('  ! Sin técnicos demo activos. Ejecuta sin --skip-users primero.')
            return 0

        today = timezone.localdate()
        tz    = timezone.get_current_timezone()
        total = 0

        def _pick(company):
            if company == 'wom':
                t = random.choice(techs_wom or techs_pti)
                s = random.choice(sites_wom or sites_pti)
            else:
                t = random.choice(techs_pti or techs_wom)
                s = random.choice(sites_pti or sites_wom)
            return t, s

        def _note(extra: str = '') -> str:
            return f'[DEMO]{" " + extra if extra else ""}'

        # 1. COMPLETADAS — últimos 30 días (15 visitas)
        for i in range(15):
            days_ago = random.randint(1, 30)
            sched    = today - timedelta(days=days_ago)
            company  = 'wom' if i % 2 == 0 else 'pti'
            tech, site = _pick(company)
            coord    = coord_wom if company == 'wom' else coord_pti
            t_start  = datetime.combine(sched, datetime.min.time()).replace(
                hour=random.randint(8, 10), minute=random.randint(0, 59), tzinfo=tz,
            )
            duration = random.randint(45, 180)
            t_end    = t_start + timedelta(minutes=duration)
            approved_at = t_start - timedelta(hours=random.randint(2, 48))
            v = Visit.objects.create(
                technician=tech, site=site, coordinator=coord,
                status=Visit.Status.COMPLETADA,
                reason=random.choice(REASONS),
                scheduled_date=sched,
                hora_inicio_trabajos=t_start,
                hora_fin_trabajos=t_end,
                approved_by=super_mgr,
                approved_at=approved_at,
                notas=_note(),
            )
            Visit.objects.filter(pk=v.pk).update(
                created_at=approved_at - timedelta(hours=random.randint(2, 72)),
            )
            _add_tracking(v, site, t_start, t_end)
            total += 1

        # 2. PROGRAMADAS — próximos 14 días (5 visitas)
        for i in range(5):
            days_ahead = random.randint(1, 14)
            sched      = today + timedelta(days=days_ahead)
            company    = 'wom' if i % 2 == 0 else 'pti'
            tech, site = _pick(company)
            coord      = coord_wom if company == 'wom' else coord_pti
            approved_at = timezone.now() - timedelta(hours=random.randint(1, 72))
            v = Visit.objects.create(
                technician=tech, site=site, coordinator=coord,
                status=Visit.Status.PROGRAMADA,
                reason=random.choice(REASONS),
                scheduled_date=sched,
                approved_by=super_mgr,
                approved_at=approved_at,
                notas=_note(),
            )
            Visit.objects.filter(pk=v.pk).update(
                created_at=approved_at - timedelta(hours=random.randint(1, 24)),
            )
            total += 1

        # 3. PENDIENTES DE APROBACIÓN — últimos 7 días (3 visitas)
        for i in range(3):
            days_ago = random.randint(0, 7)
            sched    = today - timedelta(days=days_ago)
            company  = 'wom' if i % 2 == 0 else 'pti'
            tech, site = _pick(company)
            coord    = coord_wom if company == 'wom' else coord_pti
            Visit.objects.create(
                technician=tech, site=site, coordinator=coord,
                status=Visit.Status.PENDIENTE_APROBACION,
                reason=random.choice(REASONS),
                scheduled_date=sched,
                notas=_note(),
            )
            total += 1

        # 4. EN EJECUCIÓN HOY — 4 visitas (en_camino, llegada, trabajando, finalizando)
        active_states = [
            (Visit.Status.EN_CAMINO,   ['salida'],                              1, False),
            (Visit.Status.LLEGADA,     ['salida', 'llegada'],                   2, False),
            (Visit.Status.TRABAJANDO,  ['salida', 'llegada', 'inicio'],         3, True),
            (Visit.Status.FINALIZANDO, ['salida', 'llegada', 'inicio', 'finalizado'], 4, True),
        ]
        for i, (status, events, n_pts, needs_start) in enumerate(active_states):
            company  = 'wom' if i % 2 == 0 else 'pti'
            tech, site = _pick(company)
            coord    = coord_wom if company == 'wom' else coord_pti
            t_start  = datetime.combine(today, datetime.min.time()).replace(
                hour=random.randint(7, 9), minute=random.randint(0, 30), tzinfo=tz,
            )
            approved_at = t_start - timedelta(hours=2)
            v = Visit.objects.create(
                technician=tech, site=site, coordinator=coord,
                status=status,
                reason=random.choice(REASONS),
                scheduled_date=today,
                hora_inicio_trabajos=t_start if needs_start else None,
                approved_by=super_mgr,
                approved_at=approved_at,
                notas=_note(),
            )
            Visit.objects.filter(pk=v.pk).update(
                created_at=approved_at - timedelta(hours=random.randint(1, 12)),
            )
            route = _make_route(site.latitude, site.longitude, n_pts)
            for j, (event, (lat, lng)) in enumerate(zip(events, route)):
                VisitTrackingPoint.objects.create(
                    visit=v, event=event, latitude=lat, longitude=lng,
                    timestamp=t_start + timedelta(minutes=j * 20),
                )
            total += 1

        # 5. CANCELADAS — últimos 30 días (4 visitas)
        for i in range(4):
            days_ago = random.randint(1, 30)
            sched    = today - timedelta(days=days_ago)
            company  = 'wom' if i % 2 == 0 else 'pti'
            tech, site = _pick(company)
            coord    = coord_wom if company == 'wom' else coord_pti
            Visit.objects.create(
                technician=tech, site=site, coordinator=coord,
                status=Visit.Status.CANCELADA,
                reason=random.choice(REASONS),
                scheduled_date=sched,
                notas=_note('Cancelado por solicitud del área de operaciones.'),
            )
            total += 1

        # 6. RECHAZADAS — últimos 20 días (4 visitas)
        for i in range(4):
            days_ago = random.randint(1, 20)
            sched    = today - timedelta(days=days_ago)
            company  = 'wom' if i % 2 == 0 else 'pti'
            tech, site = _pick(company)
            coord    = coord_wom if company == 'wom' else coord_pti
            Visit.objects.create(
                technician=tech, site=site, coordinator=coord,
                status=Visit.Status.RECHAZADA,
                reason=random.choice(REASONS),
                scheduled_date=sched,
                rejected_by=super_mgr,
                rejected_at=timezone.now() - timedelta(days=days_ago - 1),
                rejection_reason='Documentación incompleta. Reprogramar con antecedentes.',
                notas=_note(),
            )
            total += 1

        self.stdout.write(f'  {total} visitas creadas.')
        return total

    # ── Banner final ──────────────────────────────────────────────────────────

    def _print_banner(self, password, settings, staff, techs, visits):
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('━━━ Demo cargada correctamente ━━━'))
        self.stdout.write('')
        self.stdout.write(f'  SiteSettings : {settings} (WOM, PTI)')
        self.stdout.write(f'  Cuentas demo : {staff} (admin, supermanager, 2 managers, 2 viewers)')
        self.stdout.write(f'  Tecnicos demo: {techs} (6 WOM + 6 PTI)')
        self.stdout.write(f'  Visitas demo : {visits} (15 completadas + 5 programadas + 3 pendientes'
                          ' + 4 activas hoy + 4 canceladas + 4 rechazadas)')
        self.stdout.write('')
        self.stdout.write(f'  Password de todas las cuentas demo: {password}')
        self.stdout.write('')
        self.stdout.write('  Cuentas creadas:')
        self.stdout.write('    admin@sitevisit.demo          -> Admin Django + portal')
        self.stdout.write('    supermanager@sitevisit.demo   -> Super Manager (cross-org)')
        self.stdout.write('    manager@wom.demo              -> Coordinador WOM')
        self.stdout.write('    manager@pti.demo              -> Coordinador PTI')
        self.stdout.write('    viewer@wom.demo               -> Solo lectura WOM')
        self.stdout.write('    viewer@pti.demo               -> Solo lectura PTI')
        self.stdout.write('')
        self.stdout.write('  Tecnicos demo (12): aparecen en visitas del portal web.')
        self.stdout.write('    NO pueden loguearse en la app movil (sin device registrado).')
        self.stdout.write('')
        self.stdout.write('  Para limpiar: python manage.py flush_production_demo')
