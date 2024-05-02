from django.db import migrations

from creme.creme_core.migrations.utils import utils_26


def fill_json(apps, schema_editor):
    from creme.assistants import setting_keys

    utils_26.fill_json_for_setting_key(apps, setting_keys.todo_reminder_key)


class Migration(migrations.Migration):
    run_before = [
        ('creme_core', '0150_v2_6__settingvalue_json03')
    ]

    dependencies = [
        ('creme_core', '0148_v2_6__settingvalue_json01'),
        ('assistants', '0016_v_2_6__fix_priority_uuids'),
    ]

    operations = [
        migrations.RunPython(fill_json),
    ]
