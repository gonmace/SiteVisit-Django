from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('visits', '0002_alter_visit_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='visit',
            name='notas',
            field=models.TextField(blank=True, default=''),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='visitphoto',
            name='photo_type',
            field=models.CharField(
                choices=[
                    ('vehiculo',   'Movilidad (frente)'),
                    ('encargado',  'Encargado'),
                    ('trabajo_1',  'Imagen 1'),
                    ('trabajo_2',  'Imagen 2'),
                    ('trabajo_3',  'Imagen 3'),
                    ('trabajo_4',  'Imagen 4'),
                    ('trabajo_5',  'Imagen 5'),
                    ('trabajo_6',  'Imagen 6'),
                    ('trabajo_7',  'Imagen 7'),
                    ('trabajo_8',  'Imagen 8'),
                    ('trabajo_9',  'Imagen 9'),
                    ('trabajo_10', 'Imagen 10'),
                    ('llegada',    'Llegada al sitio'),
                    ('cierre',     'Cierre'),
                ],
                max_length=16,
            ),
        ),
    ]
