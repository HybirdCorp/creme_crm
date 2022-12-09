from django.db import migrations


def fill_entity_ctypes(apps, schema_editor):
    for model_name in ('EntityJobResult', 'MassImportJobResult'):
        for ejr in apps.get_model('creme_core', model_name).objects.exclude(entity=None):
            ejr.entity_ctype_id = ejr.entity.entity_type_id
            ejr.save()


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0095_v2_4__job_results_entity_ctype01'),
    ]

    operations = [
        migrations.RunPython(fill_entity_ctypes),
    ]
