from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('visits', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='visit',
            name='status',
            field=models.CharField(
                choices=[
                    ('programada', 'Programada'),
                    ('en_camino', 'Inicio'),
                    ('llegada', 'Sitio'),
                    ('trabajando', 'Servicios'),
                    ('completada', 'Completada'),
                    ('cancelada', 'Cancelada'),
                ],
                default='programada',
                max_length=16,
            ),
        ),
    ]
