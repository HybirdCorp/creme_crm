from django.db import migrations


def complete_instance_brick_config_items(apps, schema_editor):
    for ibci in apps.get_model('creme_core', 'InstanceBrickConfigItem').objects.all():
        ibci.entity_ctype_id = ibci.entity.entity_type_id
        ibci.save()


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0199_v3_0__instancebrickconfigitem_real_entity_fk1'),
    ]

    operations = [
        migrations.RunPython(complete_instance_brick_config_items),
    ]
