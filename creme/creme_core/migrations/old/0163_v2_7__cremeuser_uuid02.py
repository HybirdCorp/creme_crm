from uuid import uuid4

from django.db import migrations

FIXED_UUIDS = {
    1: 'f53e8537-9aae-454c-adc1-a89df9563c28',
}


def fill_uuids(apps, schema_editor):
    for instance in apps.get_model('creme_core', 'CremeUser').objects.all():
        instance.uuid = FIXED_UUIDS.get(instance.id) or uuid4()
        instance.save()


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0162_v2_7__cremeuser_uuid01'),
    ]

    operations = [
        migrations.RunPython(fill_uuids),
    ]
