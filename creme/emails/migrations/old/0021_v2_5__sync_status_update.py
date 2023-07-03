from django.db import migrations

SYNCHRONIZED         = 4
SYNCHRONIZED_SPAM    = 5
SYNCHRONIZED_WAITING = 6


def convert_deprecated_status(apps, schema_editor):
    filter_email = apps.get_model('emails', 'EntityEmail').objects.filter

    count = 0

    for email in filter_email(status=SYNCHRONIZED_WAITING):
        email.status = SYNCHRONIZED
        email.description = '\n'.join([
            email.description,
            f'Status set to SYNCHRONIZED ({SYNCHRONIZED}) automatically in Creme 2.5.',
        ]).strip()
        email.save()

        count += 1

    for email in filter_email(status=SYNCHRONIZED_SPAM):
        email.status = SYNCHRONIZED
        email.description = '\n'.join([
            email.description,
            f'Status set to SYNCHRONIZED ({SYNCHRONIZED}) + moved to trash '
            f'automatically in Creme 2.5.',
        ]).strip()
        email.is_deleted = True
        email.save()

        count += 1

    if count:
        print(
            f'    BEWARE: {count} email(s) has been marked as SYNCHRONIZED ({SYNCHRONIZED}).\n'
        )


class Migration(migrations.Migration):
    dependencies = [
        ('emails', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(convert_deprecated_status),
    ]
