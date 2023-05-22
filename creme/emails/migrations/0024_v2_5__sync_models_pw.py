from django.core import signing
from django.db import migrations

from creme.creme_core.utils.crypto import SymmetricEncrypter

salt = 'creme.emails.models.synchronization.EmailSyncConfigItem'


# Version 2.4
# def convert_pw(apps, schema_editor):
#     encrypter = SymmetricEncrypter(salt=salt)
#
#     for item in apps.get_model('emails', 'EmailSyncConfigItem').objects.all():
#         pw = signing.loads(item.encoded_password, salt=salt)
#         item.encoded_password = encrypter.encrypt(pw.encode()).decode()
#         item.save()
def convert_pw(apps, schema_editor):
    encrypter = SymmetricEncrypter(salt=salt)

    for item in apps.get_model('emails', 'EmailSyncConfigItem').objects.all():
        try:
            pw = signing.loads(item.encoded_password, salt=salt)
        except signing.BadSignature:
            print('It seems the 2.4 migration for password storage has been made.')
        else:
            item.encoded_password = encrypter.encrypt(pw.encode()).decode()
            item.save()


class Migration(migrations.Migration):
    dependencies = [
        ('emails', '0023_emailsending_config_item02'),
    ]

    operations = [
        migrations.RunPython(convert_pw),
    ]
