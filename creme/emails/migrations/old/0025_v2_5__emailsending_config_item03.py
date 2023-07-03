from django.core import signing
from django.db import migrations

from creme.creme_core.utils.crypto import SymmetricEncrypter

salt = 'creme.emails.models.sending.EmailSendingConfigItem'


def convert_pw(apps, schema_editor):
    encrypter = SymmetricEncrypter(salt=salt)

    for item in apps.get_model('emails', 'EmailSendingConfigItem').objects.exclude(encoded_password=''):
        try:
            pw = signing.loads(item.encoded_password, salt=salt)
        except signing.BadSignature:
            print(
                f'Bad signature with EmailSendingConfigItem id={item.id}; '
                f'you will have to fill the password again.'
            )
            item.encoded_password = ''
        else:
            item.encoded_password = encrypter.encrypt(pw.encode()).decode()

        item.save()


class Migration(migrations.Migration):
    dependencies = [
        ('emails', '0024_v2_5__sync_models_pw'),
    ]

    operations = [
        migrations.RunPython(convert_pw),
    ]
