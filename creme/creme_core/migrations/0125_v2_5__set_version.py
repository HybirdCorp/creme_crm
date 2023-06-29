from django.db import migrations


def set_version(apps, schema_editor):
    apps.get_model('creme_core', 'Version').objects.create(value='2.5')


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0124_v2_5__cremeentity_extra_data'),
    ]

    operations = [
        migrations.RunPython(set_version),
    ]
