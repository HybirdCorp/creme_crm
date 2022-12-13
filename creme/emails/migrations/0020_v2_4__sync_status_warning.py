from django.db import migrations

SYNCHRONIZED         = 4
SYNCHRONIZED_SPAM    = 5
SYNCHRONIZED_WAITING = 6


def warnings_for_deprecated_status(apps, schema_editor):
    filter_email = apps.get_model('emails', 'EntityEmail').objects.filter

    count_waiting = filter_email(status=SYNCHRONIZED_WAITING).count()
    count_spam    = filter_email(status=SYNCHRONIZED_SPAM).count()

    if count_waiting or count_spam:
        print('\n')

    if count_waiting:
        print(
            f'    BEWARE: you have {count_waiting} email(s) with the status '
            f'SYNCHRONIZED_WAITING ({SYNCHRONIZED_WAITING}) ;\n'
            f'            if you do not manually fix them, their status will be '
            f'set to SYNCHRONIZED ({SYNCHRONIZED}) automatically in Creme 2.5.'
        )

    if count_spam:
        print(
            f'    BEWARE: you have {count_spam} email(s) with the status SYNCHRONIZED_SPAM '
            f'({SYNCHRONIZED_SPAM}) ; if you do not manually fix them, in Creme 2.5 :\n'
            f'      - their status will be set to SYNCHRONIZED ({SYNCHRONIZED})\n'
            f'      - they will be marked as deleted'
        )


class Migration(migrations.Migration):
    dependencies = [
        ('emails', '0019_v2_4__sync_models'),
    ]

    operations = [
        migrations.RunPython(
            warnings_for_deprecated_status,
            reverse_code=warnings_for_deprecated_status,
        ),
    ]
