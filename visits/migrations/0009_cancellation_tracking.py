import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def backfill_cancellation(apps, schema_editor):
    Visit = apps.get_model('visits', 'Visit')
    # Visitas canceladas: copiar notas → cancellation_reason, limpiar notas,
    # fijar status_before_cancellation = 'pendiente_aprobacion' (única posibilidad pre-migración)
    Visit.objects.filter(status='cancelada').update(
        cancellation_reason=models.F('notas'),
        status_before_cancellation='pendiente_aprobacion',
        notas='',
    )
    # Visitas rechazadas: fijar status_before_rejection = 'pendiente_aprobacion'
    Visit.objects.filter(status='rechazada').update(
        status_before_rejection='pendiente_aprobacion',
    )


class Migration(migrations.Migration):

    dependencies = [
        ('visits', '0008_alter_visittrackingpoint_event'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='visit',
            name='status_before_rejection',
            field=models.CharField(blank=True, default='', max_length=24),
        ),
        migrations.AddField(
            model_name='visit',
            name='cancelled_by',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='cancelled_visits',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='visit',
            name='cancelled_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='visit',
            name='cancellation_reason',
            field=models.TextField(blank=True, default=''),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='visit',
            name='status_before_cancellation',
            field=models.CharField(blank=True, default='', max_length=24),
        ),
        migrations.RunPython(backfill_cancellation, migrations.RunPython.noop),
    ]
