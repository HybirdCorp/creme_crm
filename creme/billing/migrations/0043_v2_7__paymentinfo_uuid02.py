from uuid import uuid4

from django.db import migrations


def generate_UUIDs(apps, schema_editor):
    for instance in apps.get_model('billing', 'PaymentInformation').objects.all():
        instance.uuid = uuid4()
        instance.save()


class Migration(migrations.Migration):
    dependencies = [
        ('billing', '0042_v2_7__paymentinfo_uuid01'),
    ]

    operations = [
        migrations.RunPython(generate_UUIDs),
    ]
