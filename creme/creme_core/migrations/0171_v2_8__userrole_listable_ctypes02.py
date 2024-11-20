from django.db import migrations


def fix_roles(apps, schema_editor):
    for role in apps.get_model('creme_core', 'UserRole').objects.all():
        print(role)

    raise ValueError('TODO')


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0170_v2_8__userrole_listable_ctypes01'),
    ]

    operations = [
        migrations.RunPython(fix_roles),
    ]
