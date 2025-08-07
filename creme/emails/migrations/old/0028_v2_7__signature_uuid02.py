from uuid import uuid4

from django.db import migrations


def generate_UUIDs(apps, schema_editor):
    for instance in apps.get_model('emails', 'EmailSignature').objects.all():
        instance.uuid = uuid4()
        instance.save()


class Migration(migrations.Migration):
    dependencies = [
        ('emails', '0027_v2_7__signature_uuid01'),
    ]

    operations = [
        migrations.RunPython(generate_UUIDs),
    ]
