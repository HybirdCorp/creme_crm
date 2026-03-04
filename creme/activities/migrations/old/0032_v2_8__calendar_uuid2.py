from uuid import uuid4

from django.db import migrations


def generate_UUIDs(apps, schema_editor):
    for instance in apps.get_model('activities', 'Calendar').objects.all():
        instance.uuid = uuid4()
        instance.save()


class Migration(migrations.Migration):
    dependencies = [
        ('activities', '0031_v2_8__calendar_uuid1'),
    ]

    operations = [
        migrations.RunPython(generate_UUIDs),
    ]
