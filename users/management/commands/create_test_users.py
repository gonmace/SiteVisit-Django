from django.core.management.base import BaseCommand

from users.models import User

PASSWORD = 'Test1234!'

TECHNICIANS = [
    # (first_name, last_name, email, username)
    ('Carlos',    'Muñoz',     'carlos.munoz@test.cl',     'cmunoz'),
    ('María',     'González',  'maria.gonzalez@test.cl',   'mgonzalez'),
    ('Pedro',     'Soto',      'pedro.soto@test.cl',       'psoto'),
    ('Ana',       'Martínez',  'ana.martinez@test.cl',     'amartinez'),
    ('Jorge',     'Rojas',     'jorge.rojas@test.cl',      'jrojas'),
    ('Valentina', 'López',     'valentina.lopez@test.cl',  'vlopez'),
    ('Felipe',    'Hernández', 'felipe.hernandez@test.cl', 'fhernandez'),
    ('Camila',    'Vargas',    'camila.vargas@test.cl',    'cvargas'),
    ('Diego',     'Torres',    'diego.torres@test.cl',     'dtorres'),
    ('Gabriela',  'Flores',    'gabriela.flores@test.cl',  'gflores'),
    ('Roberto',   'Silva',     'roberto.silva@test.cl',    'rsilva'),
    ('Patricia',  'Morales',   'patricia.morales@test.cl', 'pmorales'),
    ('Luis',      'Araya',     'luis.araya@test.cl',       'laraya'),
    ('Carolina',  'Fuentes',   'carolina.fuentes@test.cl', 'cfuentes'),
    ('Andrés',    'Pizarro',   'andres.pizarro@test.cl',   'apizarro'),
]

USERS = [
    # (email, username, role, company, is_staff, is_superuser)
    ('admin@sitevisit.dev',      'admin',          User.Role.SUPER_MANAGER, User.Company.WOM, True,  True),
    ('supermanager@wom.cl',      'supermanager',   User.Role.SUPER_MANAGER, User.Company.WOM, False, False),
    ('manager@wom.cl',           'manager_wom',    User.Role.MANAGER,       User.Company.WOM, False, False),
    ('manager@pti.cl',           'manager_pti',    User.Role.MANAGER,       User.Company.PTI, False, False),
    ('tecnico@wom.cl',           'tecnico_wom',    User.Role.TECHNICIAN,    User.Company.WOM, False, False),
    ('viewer@wom.cl',            'viewer_wom',     User.Role.VIEWER,        User.Company.WOM, False, False),
]


class Command(BaseCommand):
    help = 'Crea usuarios de prueba con contraseña Test1234!'

    def handle(self, *args, **options):
        created_count = 0
        updated_count = 0

        for first_name, last_name, email, username in TECHNICIANS:
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username':   username,
                    'first_name': first_name,
                    'last_name':  last_name,
                    'role':       User.Role.TECHNICIAN,
                    'status':     User.Status.INACTIVE,
                },
            )
            if not created:
                user.first_name = first_name
                user.last_name  = last_name
                user.company    = ''
                user.rut        = None
                user.cargo      = ''
                user.phone      = ''
                user.status     = User.Status.INACTIVE
            user.set_password(PASSWORD)
            user.save()
            label = 'creado     ' if created else 'actualizado'
            self.stdout.write(f'  [{label}] {first_name} {last_name} <{email}>')
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write('')

        for email, username, role, company, is_staff, is_superuser in USERS:
            user = User.objects.filter(email=email).first() or User.objects.filter(username=username).first()
            created = user is None
            if created:
                user = User(email=email, username=username)
            else:
                user.email = email
                user.username = username
            user.role = role
            user.company = company
            user.is_staff = is_staff
            user.is_superuser = is_superuser
            user.status = User.Status.ACTIVE
            if not user.first_name:
                user.first_name = username.replace('_', ' ').title()
            user.set_password(PASSWORD)
            user.save()
            if created:
                created_count += 1
                self.stdout.write(f'  [+] creado      {email}  [{role}]')
            else:
                updated_count += 1
                self.stdout.write(f'  [u] actualizado {email}  [{role}]')

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'Listo: {created_count} creados, {updated_count} ya existían.'
        ))
        self.stdout.write(f'Contraseña: {PASSWORD}')
        self.stdout.write('')
        self.stdout.write('Usuarios disponibles:')
        self.stdout.write('  admin@sitevisit.dev     superusuario (admin + portal)')
        self.stdout.write('  supermanager@wom.cl     super manager (todas las empresas)')
        self.stdout.write('  manager@wom.cl          manager WOM')
        self.stdout.write('  manager@pti.cl          manager PTI')
        self.stdout.write('  tecnico@wom.cl          tecnico WOM')
        self.stdout.write('  viewer@wom.cl           solo lectura WOM')
        self.stdout.write('')
        self.stdout.write(f'Técnicos de prueba: {len(TECHNICIANS)} (sin empresa ni RUT — datos via app)')
