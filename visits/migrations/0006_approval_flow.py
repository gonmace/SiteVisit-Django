from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def backfill_approved_at(apps, schema_editor):
    Visit = apps.get_model('visits', 'Visit')
    Visit.objects.exclude(
        status='pendiente_aprobacion'
    ).filter(approved_at__isnull=True).update(
        approved_at=models.F('created_at')
    )


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('visits', '0005_visitphoto_description'),
    ]

    operations = [
        migrations.AlterField(
            model_name='visit',
            name='status',
            field=models.CharField(
                choices=[
                    ('pendiente_aprobacion', 'Pendiente de aprobación'),
                    ('programada',           'Programado'),
                    ('en_camino',            'Inicio'),
                    ('llegada',              'Sitio'),
                    ('trabajando',           'Servicio'),
                    ('completada',           'Completado'),
                    ('cancelada',            'Cancelado'),
                    ('rechazada',            'Rechazada'),
                ],
                default='pendiente_aprobacion',
                max_length=24,
            ),
        ),
        migrations.AddField(
            model_name='visit',
            name='coordinator',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='coordinated_visits',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='visit',
            name='approved_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='visit',
            name='rejected_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(backfill_approved_at, migrations.RunPython.noop),
    ]
