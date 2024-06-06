# NB: we cannot easily retrieve all SettingKeys, because 'apps.apps' is not
#     initialized. So each app has to migrate its own SettingValues.
from django.db import migrations

from creme.creme_core.migrations.utils import utils_26


def fill_json(apps, schema_editor):
    from creme.creme_core import setting_keys

    utils_26.fill_json_for_setting_key(apps, setting_keys.block_opening_key)
    utils_26.fill_json_for_setting_key(apps, setting_keys.block_showempty_key)
    utils_26.fill_json_for_setting_key(apps, setting_keys.currency_symbol_key)


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0148_v2_6__settingvalue_json01'),
    ]

    operations = [
        migrations.RunPython(fill_json),
    ]
