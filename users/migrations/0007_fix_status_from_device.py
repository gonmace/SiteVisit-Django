from django.db import migrations


def fix_status_from_device(apps, schema_editor):
    User = apps.get_model('users', 'User')
    UserDevice = apps.get_model('users', 'UserDevice')

    # Device registered but not yet approved → Pendiente (1)
    pending_ids = UserDevice.objects.filter(is_active=False).values_list('user_id', flat=True)
    User.objects.filter(id__in=pending_ids).update(status=1)

    # Device approved → Activo (2)
    active_ids = UserDevice.objects.filter(is_active=True).values_list('user_id', flat=True)
    User.objects.filter(id__in=active_ids).update(status=2)

    # No device → Inactivo (0)
    all_device_ids = UserDevice.objects.values_list('user_id', flat=True)
    User.objects.filter(role='technician').exclude(id__in=all_device_ids).update(status=0)

    # Non-technician users → always Activo
    User.objects.exclude(role='technician').update(status=2)


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0006_add_status_remove_pending_activation'),
    ]

    operations = [
        migrations.RunPython(fix_status_from_device, migrations.RunPython.noop),
    ]
