from django.db import migrations
from django.utils.timezone import now


def fix_contacts_for_staff(apps, schema_editor):
    apps.get_model('persons', 'Contact').objects.filter(is_user__is_staff=True).update(
        is_deleted=True,
        modified=now(),  # For future deletion date...
        is_user=None,
    )


class Migration(migrations.Migration):
    dependencies = [
        ('persons', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(fix_contacts_for_staff),
    ]
