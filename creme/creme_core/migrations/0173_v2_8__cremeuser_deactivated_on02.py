from django.db import migrations
from django.db.models import F
from django.db.models.functions import Coalesce


def fill_deactivation_on(apps, schema_editor):
    apps.get_model('creme_core', 'CremeUser').objects.filter(is_active=False).update(
        deactivated_on=Coalesce(F('last_login'), F('date_joined')),
    )


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0172_v2_8__cremeuser_deactivated_on01'),
    ]

    operations = [
        migrations.RunPython(fill_deactivation_on),
    ]
