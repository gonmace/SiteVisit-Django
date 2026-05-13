from django.db import migrations, models


def populate_name_and_fix_wom(apps, schema_editor):
    SiteSetting = apps.get_model('home', 'SiteSetting')
    name_map = {'wom': 'WOM', 'pti': 'PTI', 'default': 'Default'}
    for obj in SiteSetting.objects.all():
        obj.name = name_map.get(obj.slug, obj.slug.upper())
        if obj.slug == 'wom' and obj.primary != '#E6007E':
            obj.primary = '#E6007E'
        obj.save(update_fields=['name', 'primary'])


def seed_defaults(apps, schema_editor):
    SiteSetting = apps.get_model('home', 'SiteSetting')
    defaults = [
        ('wom',     'WOM',     '#E6007E'),
        ('pti',     'PTI',     '#1C2B4A'),
        ('default', 'Default', '#F15A22'),
    ]
    for slug, name, primary in defaults:
        SiteSetting.objects.get_or_create(slug=slug, defaults={'name': name, 'primary': primary})


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0002_alter_sitesetting_company'),
    ]

    operations = [
        # 1. Agregar campo name (nullable inicialmente para poder poblar después)
        migrations.AddField(
            model_name='sitesetting',
            name='name',
            field=models.CharField(default='', help_text='Nombre visible de la empresa', max_length=64),
        ),
        # 2. Renombrar company → slug (ALTER TABLE RENAME COLUMN — no toca índices)
        migrations.RenameField(
            model_name='sitesetting',
            old_name='company',
            new_name='slug',
        ),
        # 3. Cambiar tipo de CharField(choices=...) a SlugField limpio
        migrations.AlterField(
            model_name='sitesetting',
            name='slug',
            field=models.SlugField(max_length=16, unique=True,
                                   help_text='Identificador interno (wom, pti, ...)'),
        ),
        # 4. Relajar secondary y accent a blank=True, default=''
        migrations.AlterField(
            model_name='sitesetting',
            name='secondary',
            field=models.CharField(blank=True, default='',
                                   help_text='(opcional) Color secundario hex', max_length=7),
        ),
        migrations.AlterField(
            model_name='sitesetting',
            name='accent',
            field=models.CharField(blank=True, default='',
                                   help_text='(opcional) Color de acento hex', max_length=7),
        ),
        # 5. Poblar names y corregir color WOM
        migrations.RunPython(populate_name_and_fix_wom, migrations.RunPython.noop),
        # 6. Actualizar meta del modelo
        migrations.AlterModelOptions(
            name='sitesetting',
            options={'ordering': ['name'], 'verbose_name': 'empresa', 'verbose_name_plural': 'empresas'},
        ),
        # 7. Garantizar filas WOM, PTI y default (idempotente)
        migrations.RunPython(seed_defaults, migrations.RunPython.noop),
    ]
