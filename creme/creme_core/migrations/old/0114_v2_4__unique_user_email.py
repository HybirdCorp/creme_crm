from collections import defaultdict

from django.conf import settings
from django.db import migrations


def deduplicate_users_email(apps, schema_editor):
    if settings.AUTH_USER_MODEL == 'creme_core.CremeUser':
        users = defaultdict(list)

        for user in apps.get_model('creme_core', 'CremeUser').objects.filter(is_active=True):
            users[user.email].append(user)

        collision_count = 0

        for email, colliding_users in users.items():
            length = len(colliding_users)
            if length > 1:
                collision_count += length

                email_parts = email.split('@', 1)
                for i, user in enumerate(colliding_users, start=1):
                    # TODO: manage the case where the new address is longer than
                    #       the field's max-length...
                    user.email = f'{email_parts[0]}+please_update_me{i}@{email_parts[1]}'
                    user.save()

        if collision_count:
            print(
                f'\nBEWARE: {collision_count} users with colliding email addresses '
                f'have been found ; addresses have been updated with suffix '
                f'"+please_update_meXXX" so they should continue to work as is.'
            )


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0113_v2_4__worldsettings_password_fields'),
    ]

    operations = [
        migrations.RunPython(deduplicate_users_email),
    ]
