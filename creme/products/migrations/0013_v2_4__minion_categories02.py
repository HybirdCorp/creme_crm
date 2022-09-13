from uuid import uuid4

from django.db import migrations


def generate_UUIDs(apps, schema_editor):
    for model_name in ['Category', 'SubCategory']:
        for instance in apps.get_model('products', model_name).objects.all():
            instance.uuid = uuid4()
            instance.save()


class Migration(migrations.Migration):
    dependencies = [
        ('products', '0012_v2_4__minion_categories01'),
    ]

    operations = [
        migrations.RunPython(generate_UUIDs),
    ]
