from django.db import migrations


def fill_entity_ctypes(apps, schema_editor):
    for lw_email in apps.get_model(
            'emails', 'LightWeightEmail',
    ).objects.exclude(recipient_entity=None):
        lw_email.recipient_ctype_id = lw_email.recipient_entity.entity_type_id
        lw_email.save()


class Migration(migrations.Migration):
    dependencies = [
        ('emails', '0016_v2_4__lightweightemail_recipient_ctype01'),
    ]

    operations = [
        migrations.RunPython(fill_entity_ctypes),
    ]
