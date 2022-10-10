import json

from django.db import migrations

BRICK_STATE_SHOW_CFORMS_DETAILS  = 'creme_config-show_customforms_details'


def convert_brick_state(apps, schema_editor):
    for state in apps.get_model('creme_core', 'BrickState').objects.filter(
        brick_id='block_creme_config-custom_forms',
    ):
        # ct_id = state.json_extra_data[BRICK_STATE_SHOW_CFORMS_DETAILS]
        extra_data = json.loads(state.json_extra_data)
        ct_id = extra_data[BRICK_STATE_SHOW_CFORMS_DETAILS]

        # state.json_extra_data[BRICK_STATE_SHOW_CFORMS_DETAILS] = {'ctype': ct_id}
        extra_data[BRICK_STATE_SHOW_CFORMS_DETAILS] = {'ctype': ct_id}
        state.json_extra_data = json.dumps(extra_data)
        state.save()


class Migration(migrations.Migration):
    dependencies = [
        ('creme_config', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(convert_brick_state),
    ]
