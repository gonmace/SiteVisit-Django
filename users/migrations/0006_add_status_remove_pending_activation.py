from django.db import migrations, models


def migrate_status_forward(apps, schema_editor):
    User = apps.get_model('users', 'User')
    UserDevice = apps.get_model('users', 'UserDevice')

    # Device registered but not yet approved → Pendiente (1)
    pending_ids = UserDevice.objects.filter(is_active=False).values_list('user_id', flat=True)
    User.objects.filter(id__in=pending_ids).update(status=1)

    # Device approved → Activo (2)
    active_ids = UserDevice.objects.filter(is_active=True).values_list('user_id', flat=True)
    User.objects.filter(id__in=active_ids).update(status=2)

    # No device → Inactivo (0) — already the default, set explicitly for technicians
    all_device_ids = UserDevice.objects.values_list('user_id', flat=True)
    User.objects.filter(role='technician').exclude(id__in=all_device_ids).update(status=0)

    # Non-technician users (managers, viewers) → always Activo
    User.objects.exclude(role='technician').update(status=2)


def migrate_status_backward(apps, schema_editor):
    User = apps.get_model('users', 'User')
    User.objects.filter(status=0).update(pending_activation=False, is_active=False)
    User.objects.filter(status=1).update(pending_activation=True, is_active=True)
    User.objects.filter(status=2).update(pending_activation=False, is_active=True)


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0005_remove_userdevice_sim_serial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='status',
            field=models.IntegerField(
                choices=[(0, 'Inactivo'), (1, 'Pendiente'), (2, 'Activo')],
                default=0,
            ),
        ),
        migrations.RunPython(migrate_status_forward, migrate_status_backward),
        migrations.RemoveField(
            model_name='user',
            name='pending_activation',
        ),
    ]
