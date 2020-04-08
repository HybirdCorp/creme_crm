from django.db import migrations


def convert_brick_id(apps, schema_editor):
    models_2_update = [
        apps.get_model('creme_core', name)
            for name in (
                'BrickDetailviewLocation',
                'BrickHomeLocation',
                'BrickMypageLocation',
                'BrickState',
            )
    ]

    for ibci in apps.get_model('creme_core', 'InstanceBrickConfigItem').objects.all():
        old_brick_id = ibci.brick_id

        brick_id_parts = old_brick_id.split('|', 1)
        if len(brick_id_parts) != 2:
            raise ValueError(
                f'Invalid "brick_id" value in InstanceBrickConfigItem with id={ibci.id}: {old_brick_id} '
                f'(must contain at least 2 parts when splitting by "|").'
            )

        ibci.brick_class_id = brick_id_parts[0]
        ibci.save()

        new_brick_id = f'instanceblock-{ibci.id}'

        for model in models_2_update:
            model.objects.filter(brick_id=old_brick_id).update(brick_id=new_brick_id)


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0067_v2_2__instancebricks_json_data01'),
    ]

    operations = [
        migrations.RunPython(convert_brick_id),
    ]
