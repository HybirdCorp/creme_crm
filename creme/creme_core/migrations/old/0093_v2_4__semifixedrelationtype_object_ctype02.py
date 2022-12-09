from django.db import migrations


def fill_object_ctype(apps, schema_editor):
    for sfrt in apps.get_model('creme_core', 'SemiFixedRelationType').objects.all():
        sfrt.object_ctype_id = sfrt.object_entity.entity_type_id
        sfrt.save()


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0092_v2_4__semifixedrelationtype_object_ctype01'),
    ]

    operations = [
        migrations.RunPython(fill_object_ctype),
    ]
