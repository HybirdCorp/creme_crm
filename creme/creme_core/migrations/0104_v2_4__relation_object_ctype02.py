from django.db import migrations


def fill_object_ctype(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Relation = apps.get_model("creme_core", "Relation")

    for ctid in ContentType.objects.values_list("id", flat=True):
        Relation.objects.filter(object_entity__entity_type_id=ctid).update(object_ctype_id=ctid)


class Migration(migrations.Migration):

    dependencies = [
        ('creme_core', '0103_v2_4__relation_object_ctype01'),
    ]

    operations = [
        migrations.RunPython(fill_object_ctype),
    ]
