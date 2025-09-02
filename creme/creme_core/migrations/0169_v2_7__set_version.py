from django.db import migrations


def set_version(apps, schema_editor):
    apps.get_model('creme_core', 'Version').objects.create(value='2.7')


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0168_v2_7__currency_is_default02'),
    ]

    operations = [
        migrations.RunPython(set_version),
    ]
