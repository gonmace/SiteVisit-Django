import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='Photo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('object_id', models.PositiveIntegerField()),
                ('app', models.CharField(max_length=100)),
                ('etapa', models.CharField(blank=True, max_length=255)),
                ('imagen', models.ImageField(upload_to='photos/')),
                ('thumbnail', models.ImageField(blank=True, null=True, upload_to='photos/thumbs/')),
                ('descripcion', models.CharField(blank=True, max_length=255)),
                ('orden', models.IntegerField(default=0)),
                ('exif_lat', models.FloatField(blank=True, null=True)),
                ('exif_lon', models.FloatField(blank=True, null=True)),
                ('exif_datetime', models.DateTimeField(blank=True, null=True)),
                ('file_size', models.PositiveIntegerField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('content_type', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    to='contenttypes.contenttype',
                )),
            ],
            options={
                'verbose_name': 'foto',
                'verbose_name_plural': 'fotos',
                'ordering': ['orden', '-created_at'],
            },
        ),
    ]
