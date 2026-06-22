from django.db import migrations


def fix_brick_class_id(apps, schema_editor):
    for ibci in apps.get_model('creme_core', 'InstanceBrickConfigItem').objects.all():
        ibci.brick_class_id = ibci.brick_class_id.removeprefix('instance-')
        ibci.save()


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0195_v3_0__minions_disabled'),
    ]

    operations = [
        migrations.RunPython(fix_brick_class_id),
    ]
