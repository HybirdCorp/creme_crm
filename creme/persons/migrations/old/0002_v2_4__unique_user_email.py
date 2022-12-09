from django.conf import settings
from django.db import migrations


def sync_with_users_email(apps, schema_editor):
    if (
        settings.AUTH_USER_MODEL == 'creme_core.CremeUser'
        and settings.PERSONS_CONTACT_MODEL == 'persons.Contact'
    ):
        filter_contact = apps.get_model('persons', 'Contact').objects.filter

        for user in apps.get_model('creme_core', 'CremeUser').objects.filter(
            is_active=True,
            email__contains='+',
        ):
            filter_contact(is_user=user).update(email=user.email)


class Migration(migrations.Migration):
    dependencies = [
        ('persons', '0001_initial'),
        ('creme_core', '0114_v2_4__unique_user_email'),
    ]

    operations = [
        migrations.RunPython(sync_with_users_email),
    ]
