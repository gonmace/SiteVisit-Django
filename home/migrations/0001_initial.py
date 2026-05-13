from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='SiteSetting',
            fields=[
                ('id',        models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('company',   models.CharField(choices=[('wom', 'WOM'), ('pti', 'PTI'), ('default', 'Default (PTI)')], default='default', max_length=16, unique=True, verbose_name='empresa')),
                ('primary',   models.CharField(default='#F15A22', help_text='Color primario hex (#RRGGBB)', max_length=7)),
                ('secondary', models.CharField(default='#1C2B4A', help_text='Color secundario hex', max_length=7)),
                ('accent',    models.CharField(default='#FF8C00', help_text='Color de acento hex', max_length=7)),
                ('logo_url',  models.URLField(blank=True, help_text='URL del logo SVG/PNG (opcional)')),
            ],
            options={
                'verbose_name': 'configuración de tema',
                'verbose_name_plural': 'configuraciones de tema',
            },
        ),
    ]
