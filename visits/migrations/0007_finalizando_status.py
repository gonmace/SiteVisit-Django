from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('visits', '0006_approval_flow'),
    ]

    operations = [
        migrations.AlterField(
            model_name='visit',
            name='status',
            field=models.CharField(
                max_length=24,
                choices=[
                    ('pendiente_aprobacion', 'Pendiente de aprobación'),
                    ('programada',           'Programado'),
                    ('en_camino',            'Inicio'),
                    ('llegada',              'Sitio'),
                    ('trabajando',           'Servicio'),
                    ('finalizando',          'Finalizando'),
                    ('completada',           'Completado'),
                    ('cancelada',            'Cancelado'),
                    ('rechazada',            'Rechazada'),
                ],
                default='pendiente_aprobacion',
            ),
        ),
    ]
