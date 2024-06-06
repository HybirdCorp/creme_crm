from uuid import uuid4

from django.db import migrations


def fill_uuids(apps, schema_editor):
    for instance in apps.get_model('creme_core', 'UserRole').objects.all():
        instance.uuid = uuid4()
        instance.save()


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0141_v2_6__userrole_extra_data_n_uuid01'),
    ]

    operations = [
        migrations.RunPython(fill_uuids),
    ]
