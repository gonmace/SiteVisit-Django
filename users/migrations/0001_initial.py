import django.contrib.auth.models
import django.contrib.auth.validators
import django.utils.timezone
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id',           models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password',     models.CharField(max_length=128, verbose_name='password')),
                ('last_login',   models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('username',     models.CharField(error_messages={'unique': 'A user with that username already exists.'}, help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.', max_length=150, unique=True, validators=[django.contrib.auth.validators.UnicodeUsernameValidator()], verbose_name='username')),
                ('first_name',   models.CharField(blank=True, max_length=150, verbose_name='first name')),
                ('last_name',    models.CharField(blank=True, max_length=150, verbose_name='last name')),
                ('is_staff',     models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                ('is_active',    models.BooleanField(default=True, help_text='Designates whether this user should be treated as active.', verbose_name='active')),
                ('date_joined',  models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('email',        models.EmailField(max_length=254, unique=True, verbose_name='email address')),
                ('role',         models.CharField(choices=[('technician', 'Técnico'), ('manager', 'Manager'), ('super_manager', 'Super Manager'), ('viewer', 'Solo lectura')], default='technician', max_length=16)),
                ('company',      models.CharField(blank=True, choices=[('wom', 'WOM'), ('pti', 'PTI')], max_length=8)),
                ('rut',          models.CharField(blank=True, default=None, max_length=20, null=True, unique=True)),
                ('cargo',        models.CharField(blank=True, max_length=64)),
                ('phone',        models.CharField(blank=True, max_length=20)),
                ('pending_activation', models.BooleanField(default=True)),
                ('groups',       models.ManyToManyField(blank=True, help_text='The groups this user belongs to.', related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions')),
            ],
            options={
                'verbose_name': 'usuario',
                'verbose_name_plural': 'usuarios',
            },
            bases=(django.contrib.auth.models.AbstractUser,),
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name='UserDevice',
            fields=[
                ('id',           models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fingerprint',  models.CharField(max_length=64)),
                ('imei',         models.CharField(blank=True, max_length=20)),
                ('sim_serial',   models.CharField(blank=True, max_length=30)),
                ('manufacturer', models.CharField(blank=True, max_length=64)),
                ('model',        models.CharField(blank=True, max_length=64)),
                ('os_version',   models.CharField(blank=True, max_length=20)),
                ('registered_at', models.DateTimeField(auto_now_add=True)),
                ('is_active',    models.BooleanField(default=False)),
                ('user',         models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='device', to='users.user')),
            ],
            options={
                'verbose_name': 'dispositivo',
                'verbose_name_plural': 'dispositivos',
            },
        ),
        migrations.CreateModel(
            name='ProfilePhoto',
            fields=[
                ('id',          models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image',       models.ImageField(upload_to='profile_photos/')),
                ('taken_at',    models.DateTimeField(blank=True, null=True)),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('user',        models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profile_photo', to='users.user')),
            ],
            options={
                'verbose_name': 'foto de perfil',
                'verbose_name_plural': 'fotos de perfil',
            },
        ),
    ]
