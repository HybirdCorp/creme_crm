from django.conf import settings
from django.core import signing
from django.db import migrations

SETTING_EMAILCAMPAIGN_SENDER = 'emails-emailcampaign_sender'


def convert_settings(apps, schema_editor):
    host = getattr(settings, 'EMAILCAMPAIGN_HOST', 'localhost')
    username = getattr(settings, 'EMAILCAMPAIGN_HOST_USER', '')
    password = getattr(settings, 'EMAILCAMPAIGN_PASSWORD', '')

    if host and username and password:
        svalue = apps.get_model('creme_core', 'SettingValue').objects.filter(
            key_id=SETTING_EMAILCAMPAIGN_SENDER,
        ).first()

        apps.get_model('emails', 'EmailSendingConfigItem').objects.create(
            name='Auto (migration v2.5)',
            host=host,
            username=username,
            # password=...,
            encoded_password=signing.dumps(
                password,
                # salt='creme.emails.models.campaign.EmailSendingConfigItem',
                salt='creme.emails.models.sending.EmailSendingConfigItem',
                # serializer=...,
                # compress=...,
            ),
            port=getattr(settings, 'EMAILCAMPAIGN_PORT', 25),
            use_tls=getattr(settings, 'EMAILCAMPAIGN_USE_TLS', True),
            default_sender=svalue.value_str if svalue is not None else '',
        )


def delete_setting_value(apps, schema_editor):
    apps.get_model('creme_core', 'SettingValue').objects.filter(
        key_id=SETTING_EMAILCAMPAIGN_SENDER,
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('emails', '0022_emailsending_config_item01'),
    ]

    operations = [
        migrations.RunPython(convert_settings),
        migrations.RunPython(delete_setting_value),
    ]
