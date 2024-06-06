from django.db import migrations


def fix_regular_brick_ids(apps, schema_editor):
    old_prefix = 'block_'
    new_prefix = 'regular-'

    for model_name in (
        'BrickDetailviewLocation', 'BrickHomeLocation', 'BrickMypageLocation', 'BrickState'
    ):
        for instance in apps.get_model('creme_core', model_name).objects.filter(
            brick_id__startswith=old_prefix,
        ):
            instance.brick_id = instance.brick_id.replace(old_prefix, new_prefix, 1)
            instance.save()


def fix_model_brick_ids(apps, schema_editor):
    apps.get_model(
        'creme_core', 'BrickDetailviewLocation'
    ).objects.filter(brick_id='modelblock',).update(brick_id='model')
    apps.get_model(
        'creme_core', 'BrickState'
    ).objects.filter(brick_id='modelblock',).update(brick_id='model')


def fix_hat_brick_ids(apps, schema_editor):
    for model_name in ('BrickDetailviewLocation', 'BrickState'):
        for instance in apps.get_model('creme_core', model_name).objects.filter(
            brick_id__startswith='hatbrick-',
        ):
            instance.brick_id = instance.brick_id.replace('hatbrick-', 'hat-', 1)
            instance.save()


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0139_v2_6__notifications'),
    ]

    operations = [
        migrations.RunPython(fix_regular_brick_ids),
        migrations.RunPython(fix_model_brick_ids),
        migrations.RunPython(fix_hat_brick_ids),
    ]
