from django.db import migrations


def _convert_json_cells(apps, custom_fields, model_name, json_cells):
    changed = False
    cells_dicts = []

    for cell_dict in json_cells:
        if cell_dict['type'] == 'custom_field':
            changed = True

            cfield_id = cell_dict['value']
            cfield_uuid = custom_fields.get(cfield_id)
            if cfield_uuid is None:
                print(f'{model_name}: the CustomField id="{cfield_id}" is not found.')
                continue

            cells_dicts.append({'type': 'custom_field', 'value': str(cfield_uuid)})
        else:
            cells_dicts.append(cell_dict)

    return changed, cells_dicts


def _convert_json_cells_field(apps, custom_fields, model_name):
    for instance in apps.get_model('creme_core', model_name).objects.all():
        changed, cells_dicts = _convert_json_cells(
            apps=apps,
            custom_fields=custom_fields,
            model_name=model_name,
            json_cells=instance.json_cells,
        )
        if changed:
            instance.json_cells = cells_dicts
            instance.save()


def _fix_header_filters(apps, custom_fields):
    _convert_json_cells_field(
        apps=apps, custom_fields=custom_fields, model_name='HeaderFilter',
    )


def _fix_search(apps, custom_fields):
    _convert_json_cells_field(
        apps=apps, custom_fields=custom_fields, model_name='SearchConfigItem',
    )


def _fix_custom_bricks(apps, custom_fields):
    _convert_json_cells_field(
        apps=apps, custom_fields=custom_fields, model_name='CustomBrickConfigItem',
    )


def _fix_relation_bricks(apps, custom_fields):
    model_name = 'RelationBrickItem'

    for instance in apps.get_model('creme_core', model_name).objects.all():
        total_changed = False
        json_cells_map = {}

        for ct_id, json_cells in instance.json_cells_map.items():
            changed, cells_dicts = _convert_json_cells(
                apps=apps,
                custom_fields=custom_fields,
                model_name=model_name,
                json_cells=json_cells,
            )
            total_changed = total_changed or changed
            json_cells_map[ct_id] = cells_dicts

        if total_changed:
            instance.json_cells_map = json_cells_map
            instance.save()


def _fix_custom_forms(apps, custom_fields):
    model_name = 'CustomFormConfigItem'

    for instance in apps.get_model('creme_core', model_name).objects.all():
        total_changed = False
        json_groups = []

        for group in instance.json_groups:
            if 'cells' in group:
                changed, cells_dicts = _convert_json_cells(
                    apps=apps,
                    custom_fields=custom_fields,
                    model_name=model_name,
                    json_cells=group['cells'],
                )
                total_changed = total_changed or changed
                json_group = {**group, 'cells': cells_dicts}
            else:  # NB: special group with just on key "group_id"
                json_group = group

            json_groups.append(json_group)

        if total_changed:
            instance.json_groups = json_groups
            instance.save()


def fix_cells(apps, schema_editor):
    custom_fields = {
        str(cf_id): cf_uuid
        for cf_id, cf_uuid in apps.get_model(
            'creme_core', 'CustomField'
        ).objects.values_list('id', 'uuid')
    }

    if custom_fields:
        _fix_header_filters(apps=apps, custom_fields=custom_fields)
        _fix_search(apps=apps, custom_fields=custom_fields)
        _fix_custom_bricks(apps=apps, custom_fields=custom_fields)
        _fix_relation_bricks(apps=apps, custom_fields=custom_fields)
        _fix_custom_forms(apps=apps, custom_fields=custom_fields)


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0156_v2_7__fileref_description'),
    ]

    operations = [
        migrations.RunPython(fix_cells),
    ]
