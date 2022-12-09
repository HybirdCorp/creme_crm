from django.db import migrations


def update_brick_ids(apps, schema_editor):
    rb_item_ids = dict(
        apps.get_model('creme_core', 'RelationBrickItem')
            .objects
            .values_list('brick_id', 'id')
    )

    for model_name in ('BrickDetailviewLocation', 'BrickState'):
        for obj in apps.get_model('creme_core', model_name).objects.filter(
            brick_id__startswith='specificblock_',
        ):
            obj.brick_id = f'rtype_brick-{rb_item_ids[obj.brick_id]}'
            obj.save()


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0100_v2_4__imprint_entity_ctype03'),
    ]

    operations = [
        migrations.RunPython(update_brick_ids),
    ]
