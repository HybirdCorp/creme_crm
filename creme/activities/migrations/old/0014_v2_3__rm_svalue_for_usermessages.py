from django.db import migrations


def remove_old_setting_value(apps, schema_editor):
    apps.get_model('creme_core', 'SettingValue').objects.filter(
        key_id='activities-form_user_messages',  # SETTING_FORM_USERS_MSG
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('activities', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(remove_old_setting_value),
    ]
