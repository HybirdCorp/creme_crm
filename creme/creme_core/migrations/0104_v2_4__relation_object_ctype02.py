from django.db import migrations


def fill_object_ctype(apps, schema_editor):
    for relation in apps.get_model('creme_core', 'Relation').objects.select_related('object_entity'):
        relation.object_ctype_id = relation.object_entity.entity_type_id
        relation.save()


class Migration(migrations.Migration):

    dependencies = [
        ('creme_core', '0103_v2_4__relation_object_ctype01'),
    ]

    operations = [
        migrations.RunPython(fill_object_ctype),
    ]
