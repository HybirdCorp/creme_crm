from django.db import migrations


def fill_entity_ctypes(apps, schema_editor):
    for imprint in apps.get_model('creme_core', 'Imprint').objects.all():
        imprint.entity_ctype_id = imprint.entity.entity_type_id
        imprint.save()


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0098_v2_4__imprint_entity_ctype01'),
    ]

    operations = [
        migrations.RunPython(fill_entity_ctypes),
    ]
