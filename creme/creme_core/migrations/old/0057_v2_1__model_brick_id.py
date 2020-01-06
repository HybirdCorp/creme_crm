from django.db import migrations


def change_old_ids(apps, schema_editor):
    apps.get_model('creme_core', 'BrickDetailviewLocation')\
        .objects \
        .filter(brick_id__startswith='modelblock_')\
        .update(brick_id='modelblock')


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0056_v2_1__brickstate_json_extra_data'),
    ]

    operations = [
        migrations.RunPython(change_old_ids),
    ]
