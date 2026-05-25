from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0004_alter_sitesetting_logo_url_alter_sitesetting_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='AppRelease',
            fields=[
                ('id',          models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('apk',         models.FileField(help_text='Archivo APK de la app Android', upload_to='releases/')),
                ('version',     models.CharField(blank=True, help_text='Ej: 1.2.3', max_length=20)),
                ('notes',       models.TextField(blank=True, help_text='Notas de la versión (opcional)')),
                ('uploaded_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name':        'release de app',
                'verbose_name_plural': 'releases de app',
                'ordering':            ['-uploaded_at'],
            },
        ),
    ]
