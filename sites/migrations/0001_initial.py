from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Site',
            fields=[
                ('id',         models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code',       models.CharField(max_length=20, unique=True)),
                ('name',       models.CharField(max_length=128)),
                ('address',    models.CharField(blank=True, max_length=256)),
                ('latitude',   models.FloatField()),
                ('longitude',  models.FloatField()),
                ('company',    models.CharField(choices=[('wom', 'WOM'), ('pti', 'PTI')], max_length=8)),
                ('is_active',  models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'sitio',
                'verbose_name_plural': 'sitios',
                'ordering': ['code'],
            },
        ),
    ]
