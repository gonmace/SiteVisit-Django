import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('sites', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Visit',
            fields=[
                ('id',                   models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status',               models.CharField(choices=[('pendiente', 'Pendiente'), ('aprobada', 'Aprobada'), ('rechazada', 'Rechazada'), ('en_camino', 'En camino'), ('llegada', 'En el sitio'), ('trabajando', 'Trabajando'), ('completada', 'Completada'), ('cancelada', 'Cancelada')], default='pendiente', max_length=16)),
                ('reason',               models.TextField()),
                ('scheduled_date',       models.DateField()),
                ('eta',                  models.TimeField(blank=True, null=True)),
                ('hora_inicio_trabajos', models.DateTimeField(blank=True, null=True)),
                ('hora_fin_trabajos',    models.DateTimeField(blank=True, null=True)),
                ('rejection_reason',     models.TextField(blank=True)),
                ('created_at',           models.DateTimeField(auto_now_add=True)),
                ('technician', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='visits', to=settings.AUTH_USER_MODEL)),
                ('site',       models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='visits', to='sites.site')),
                ('approved_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='approved_visits', to=settings.AUTH_USER_MODEL)),
                ('rejected_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='rejected_visits', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'visita',
                'verbose_name_plural': 'visitas',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='VisitPhoto',
            fields=[
                ('id',          models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('photo_type',  models.CharField(choices=[('vehiculo', 'Movilidad (frente)'), ('encargado', 'Encargado'), ('trabajo_1', 'Trabajo 1'), ('trabajo_2', 'Trabajo 2'), ('trabajo_3', 'Trabajo 3'), ('llegada', 'Llegada al sitio'), ('cierre', 'Cierre')], max_length=16)),
                ('image',       models.ImageField(upload_to='visits/%Y/%m/')),
                ('latitude',    models.FloatField(blank=True, null=True)),
                ('longitude',   models.FloatField(blank=True, null=True)),
                ('metadata',    models.JSONField(default=dict)),
                ('taken_at',    models.DateTimeField()),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('visit',       models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='photos', to='visits.visit')),
            ],
            options={
                'verbose_name': 'foto de visita',
                'verbose_name_plural': 'fotos de visitas',
            },
        ),
        migrations.CreateModel(
            name='VisitTrackingPoint',
            fields=[
                ('id',          models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event',       models.CharField(choices=[('salida', 'Salida'), ('llegada', 'Llegada'), ('inicio', 'Inicio de trabajos'), ('cierre', 'Cierre de trabajos')], max_length=16)),
                ('latitude',    models.FloatField()),
                ('longitude',   models.FloatField()),
                ('timestamp',   models.DateTimeField()),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('visit',       models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tracking_points', to='visits.visit')),
            ],
            options={
                'verbose_name': 'punto de tracking',
                'verbose_name_plural': 'puntos de tracking',
                'ordering': ['timestamp'],
            },
        ),
    ]
