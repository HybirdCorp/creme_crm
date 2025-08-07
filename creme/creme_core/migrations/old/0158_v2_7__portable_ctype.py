from django.db import migrations


def fix_ctypes(apps, schema_editor):
    ContentType = apps.get_model('contenttypes', 'ContentType')

    def ctype_key(ct_id):
        ctype = ContentType.objects.get(id=ct_id)
        return f'{ctype.app_label}.{ctype.model}'

    for rbi in apps.get_model('creme_core', 'RelationBrickItem').objects.all():
        json_cells_map = rbi.json_cells_map

        if json_cells_map:
            rbi.json_cells_map = {
                ctype_key(ct_id): cells_dicts
                for ct_id, cells_dicts in json_cells_map.items()
            }
            rbi.save()


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0157_v2_7__portable_entity_cells'),
    ]

    operations = [
        migrations.RunPython(fix_ctypes),
    ]
