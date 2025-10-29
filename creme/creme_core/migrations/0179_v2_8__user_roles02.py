from django.db import migrations


def fill_roles(apps, schema_editor):
    for user in apps.get_model('creme_core', 'CremeUser').objects.exclude(role=None):
        user.roles.set([user.role])


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0178_v2_8__user_roles01'),
    ]

    operations = [
        migrations.RunPython(fill_roles),
    ]
