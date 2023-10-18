from uuid import uuid4

from django.db import migrations


def copy_custom_items(apps, schema_editor):
    get_or_create_item = apps.get_model(
        'creme_core', 'CustomBrickConfigItem'
    ).objects.get_or_create

    for old_item in apps.get_model('creme_core', 'OldCustomBrickConfigItem').objects.all():
        get_or_create_item(
            old_id=old_item.id,
            defaults={
                'uuid': uuid4(),
                'name': old_item.name,
                'json_cells': old_item.json_cells,
                'content_type': old_item.content_type,
            },
        )


def fill_uuids(apps, schema_editor):
    for model_name in ('RelationBrickItem', 'InstanceBrickConfigItem'):
        for instance in apps.get_model('creme_core', model_name).objects.all():
            instance.uuid = uuid4()
            instance.save()


def convert_brick_ids(apps, schema_editor):
    get_model = apps.get_model
    models_with_brick_id =[
        get_model('creme_core', 'BrickDetailviewLocation'),
        get_model('creme_core', 'BrickHomeLocation'),
        get_model('creme_core', 'BrickMypageLocation'),
        get_model('creme_core', 'BrickState'),
    ]

    for rbi in get_model('creme_core', 'RelationBrickItem').objects.all():
        for model_with_brick_id in models_with_brick_id:
            model_with_brick_id.objects.filter(
                brick_id=f'rtype_brick-{rbi.id}',
            ).update(brick_id=f'rtype-{rbi.uuid}')

    for ibci in get_model('creme_core', 'InstanceBrickConfigItem').objects.all():
        for model_with_brick_id in models_with_brick_id:
            model_with_brick_id.objects.filter(
                brick_id=f'instanceblock-{ibci.id}',
            ).update(brick_id=f'instance-{ibci.uuid}')

        ibci.brick_class_id = ibci.brick_class_id.replace('instanceblock_', 'instance-')
        ibci.save()

    for cbci in get_model('creme_core', 'CustomBrickConfigItem').objects.all():
        for model_with_brick_id in models_with_brick_id:
            model_with_brick_id.objects.filter(
                brick_id=f'customblock-{cbci.old_id}',
            ).update(brick_id=f'custom-{cbci.uuid}')


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0136_v2_6__brick_config_uuid01'),
    ]

    operations = [
        migrations.RunPython(copy_custom_items),
        migrations.RunPython(fill_uuids),
        migrations.RunPython(convert_brick_ids),
    ]
