from django.db import migrations


def fill_cells_json(apps, schema_editor):
    for sci in apps.get_model('creme_core', 'SearchConfigItem').objects.all():
        field_names = sci.field_names.split(',') if sci.field_names else ()
        sci.json_cells = [
            {
                'type': 'regular_field',
                'value': field_name,
            }
            for field_name in field_names
        ]
        sci.save()


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0079_v2_2__global_search_customfields01'),
    ]

    operations = [
        migrations.RunPython(fill_cells_json),
    ]
