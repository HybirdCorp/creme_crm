from django.core import signing
from django.db import migrations

from creme.creme_core.utils.crypto import SymmetricEncrypter

salt = 'creme.emails.models.synchronization.EmailSyncConfigItem'


def convert_pw(apps, schema_editor):
    encrypter = SymmetricEncrypter(salt=salt)

    for item in apps.get_model('emails', 'EmailSyncConfigItem').objects.all():
        pw = signing.loads(item.encoded_password, salt=salt)
        item.encoded_password = encrypter.encrypt(pw.encode()).decode()
        item.save()



class Migration(migrations.Migration):
    dependencies = [
        ('emails', '0020_v2_4__sync_status_warning'),
    ]

    operations = [
        migrations.RunPython(convert_pw),
    ]
