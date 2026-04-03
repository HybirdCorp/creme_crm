from django.db import migrations


def set_version(apps, schema_editor):
    apps.get_model('creme_core', 'Version').objects.create(value='2.8')


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0185_v2_8__customfield_default_value'),
    ]

    operations = [
        migrations.RunPython(set_version),
    ]
