from django.db import migrations


def fill_entity_ctype(apps, schema_editor):
    for root_node in apps.get_model('graphs', 'RootNode').objects.all():
        root_node.entity_ctype_id = root_node.entity.entity_type_id
        root_node.save()


class Migration(migrations.Migration):
    dependencies = [
        ('graphs', '0002_v2_4__rootnode_entity_ctype01'),
    ]

    operations = [
        migrations.RunPython(fill_entity_ctype),
    ]
