from django.db import migrations


def set_version(apps, schema_editor):
    apps.get_model('creme_core', 'Version').objects.create(value='2.6')


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0154_v2_6__customfield_enumvalue_uuid03'),
    ]

    operations = [
        migrations.RunPython(set_version),
    ]
