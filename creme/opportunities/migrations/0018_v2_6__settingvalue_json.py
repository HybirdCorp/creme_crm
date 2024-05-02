from django.db import migrations

from creme.creme_core.migrations.utils import utils_26


def fill_json(apps, schema_editor):
    from creme.opportunities import setting_keys

    utils_26.fill_json_for_setting_key(apps, setting_keys.quote_key)
    utils_26.fill_json_for_setting_key(apps, setting_keys.target_constraint_key)
    utils_26.fill_json_for_setting_key(apps, setting_keys.emitter_constraint_key)


class Migration(migrations.Migration):
    run_before = [
        ('creme_core', '0150_v2_6__settingvalue_json03')
    ]

    dependencies = [
        ('creme_core', '0148_v2_6__settingvalue_json01'),
        ('opportunities', '0017_v2_6__fix_uuids'),
    ]

    operations = [
        migrations.RunPython(fill_json),
    ]
