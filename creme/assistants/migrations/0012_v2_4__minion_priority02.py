
from uuid import uuid4

from django.db import migrations


def generate_UUIDs(apps, schema_editor):
    for instance in apps.get_model('assistants', 'UserMessagePriority').objects.all():
        instance.uuid = uuid4()
        instance.save()


class Migration(migrations.Migration):
    dependencies = [
        ('assistants', '0011_v2_4__minion_priority01'),
    ]

    operations = [
        migrations.RunPython(generate_UUIDs),
    ]
