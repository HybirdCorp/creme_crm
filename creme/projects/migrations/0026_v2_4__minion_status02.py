from uuid import uuid4

from django.db import migrations


def generate_UUIDs(apps, schema_editor):
    for model_name in ['ProjectStatus', 'TaskStatus']:
        for instance in apps.get_model('projects', model_name).objects.all():
            instance.uuid = uuid4()
            instance.save()


class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0025_v2_4__minion_status01'),
    ]

    operations = [
        migrations.RunPython(generate_UUIDs),
    ]
