from uuid import uuid4

from django.db import migrations


def generate_UUIDs(apps, schema_editor):
    for model_name in ['Civility', 'LegalForm', 'Position', 'Sector', 'StaffSize']:
        for instance in apps.get_model('persons', model_name).objects.all():
            instance.uuid = uuid4()
            instance.save()


class Migration(migrations.Migration):
    dependencies = [
        ('persons', '0028_v2_4__minion_models01'),
    ]

    operations = [
        migrations.RunPython(generate_UUIDs),
    ]
