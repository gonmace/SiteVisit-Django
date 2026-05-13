from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0007_fix_status_from_device'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='status_changed_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='+',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='status_changed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
