from django.db import migrations


def fix_cforms(apps, schema_editor):
    filter_item = apps.get_model('creme_core', 'CustomFormConfigItem').objects.filter
    forbidden_cells = (
        {"type": 'cform_special', 'value': 'relations'},
        {"type": 'cform_special', 'value': 'properties'}
    )

    for descriptor_id in (
        'persons-contact_edition',
        'persons-organisation_edition',
    ):
        for item in filter_item(descriptor_id=descriptor_id):
            groups = item.json_groups
            changed = False

            for group in groups:
                cells_desc = group.get('cells')

                if cells_desc:
                    for cell in forbidden_cells:
                        try:
                            cells_desc.remove(cell)
                        except ValueError:
                            pass
                        else:
                            changed = True

            if changed:
                item.json_groups = groups
                item.save()


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0110_v2_4__customformconfigitem_jsonfield'),
        ('persons', '0030_v2_4__minion_models03'),
    ]

    operations = [
        migrations.RunPython(fix_cforms),
    ]
