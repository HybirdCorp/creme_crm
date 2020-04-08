from json import dumps as json_dump

from django.db import migrations

RFT_FIELD    = 1
RFT_RELATION = 2

RGF_NOLINK   = 'reports-no_link'
RGF_FK       = 'reports-fk'
RGF_RELATION = 'reports-relation'


def convert_brick_data(apps, schema_editor):
    for ibci in apps.get_model('creme_core', 'InstanceBrickConfigItem').objects.filter(
        brick_class_id='instanceblock_reports-graph',
    ):
        data_dict = {}

        if ibci.data:
            try:
                volatile_column, rfield_type_str = ibci.data.split('|', 1)
                rfield_type = int(rfield_type_str)
            except ValueError as e:
                raise ValueError(
                    f'Invalid data for report graph block in '
                    f'InstanceBrickConfigItem(id={ibci.id}, data="{ibci.data}"): [{e}]'
                ) from e

            if rfield_type == RFT_FIELD:
                data_dict['type'] = RGF_FK
            elif rfield_type == RFT_RELATION:
                data_dict['type'] = RGF_RELATION
            else:
                raise ValueError(
                    f'Invalid volatile type for report graph block in '
                    f'InstanceBrickConfigItem(id={ibci.id}, data="{ibci.data}")'
                )

            data_dict['value'] = volatile_column
        else:
            data_dict['type'] = RGF_NOLINK

        ibci.json_extra_data = json_dump(data_dict)
        ibci.save()


class Migration(migrations.Migration):
    dependencies = [
        ('reports',    '0012_v2_2__ordinate_field_rework03'),
        ('creme_core', '0068_v2_2__instancebricks_json_data02'),
    ]

    run_before = [
        ('creme_core', '0069_v2_2__instancebricks_json_data03'),
    ]

    operations = [
        migrations.RunPython(convert_brick_data),
    ]
