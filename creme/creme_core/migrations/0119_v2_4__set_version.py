from django.db import migrations


def remove_sessions(apps, schema_editor):
    apps.get_model('sessions', 'Session').objects.all().delete()


def set_version(apps, schema_editor):
    apps.get_model('creme_core', 'Version').objects.create(value='2.4')


class Migration(migrations.Migration):
    dependencies = [
        ('sessions', '0001_initial'),
        ('creme_core', '0118_v2_4__fileref_extra_data'),
    ]

    operations = [
        migrations.RunPython(remove_sessions),
        migrations.RunPython(set_version),
    ]
