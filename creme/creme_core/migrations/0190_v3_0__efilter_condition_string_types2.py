from django.db import migrations

types_map ={
    1: 'subfilter',
    5: 'regular_field',
    6: 'regular_date',
    20: 'custom_field',
    21: 'custom_date',
    10: 'relation',
    11: 'related_subfilter',
    15: 'property',
}


def convert_filter(apps, schema_editor):
    filter_cond = apps.get_model('creme_core', 'EntityFilterCondition').objects.filter

    for old_type_id, new_type_id in types_map.items():
        filter_cond(old_type=old_type_id).update(type=new_type_id)


def convert_workflow(apps, schema_editor):
    for wf in apps.get_model('creme_core', 'WorkFlow').objects.exclude(
        json_conditions='[]',
    ):
        # [
        #   {
        #     "entity": {"type": "edited_entity", "model": "opportunities.opportunity"},
        #     "conditions": [
        #       {
        #         "type": 5,
        #         "name": "sales_phase__won",
        #         "value": {"operator": "contains", "values": [true]}
        #       },
        #       {...}, ...
        #     ]
        #   }, {...}, ...
        # ]
        all_conditions = wf.json_conditions
        for source_conditions in all_conditions:
            for cond in source_conditions['conditions']:
                cond['type'] = types_map[cond['type']]

        wf.json_conditions = all_conditions
        wf.save()


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0189_v3_0__efilter_condition_string_types1'),
    ]

    operations = [
        migrations.RunPython(convert_filter),
        migrations.RunPython(convert_workflow),
    ]
