from uuid import uuid4

from django.db import migrations


def fill_uuids(apps, schema_editor):
    for instance in apps.get_model('creme_core', 'CustomFieldEnumValue').objects.all():
        instance.uuid = uuid4()
        instance.save()


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0152_v2_6__customfield_enumvalue_uuid01'),
    ]

    operations = [
        migrations.RunPython(fill_uuids),
    ]
