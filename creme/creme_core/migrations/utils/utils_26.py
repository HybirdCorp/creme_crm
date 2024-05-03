# Will be removed in Creme 2.7

# HINT: use this function in your own migrations
def fill_json_for_setting_key(apps, setting_key):
    from creme.creme_core.core.setting_key import _SettingKey

    for sv in apps.get_model('creme_core', 'SettingValue').objects.filter(key_id=setting_key.id):
        if setting_key.type in (_SettingKey.STRING, _SettingKey.EMAIL):
            final_value = sv.value_str
        elif setting_key.type in (_SettingKey.INT, _SettingKey.HOUR):
            final_value = int(sv.value_str) if sv.value_str else None
        elif setting_key.type == _SettingKey.BOOL:
            final_value = (sv.value_str == 'True')
        else:
            raise ValueError(
                f'The SettingKey {setting_key} has an unknown type <{setting_key.type}>.'
            )

        sv.json_value = final_value
        sv.save()
