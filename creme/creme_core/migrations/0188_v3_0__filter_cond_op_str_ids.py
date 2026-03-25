from django.db import migrations

operators_map = {
    1:  'equals',             # EQUALS
    2:  'iequals',            # IEQUALS
    3:  'equals_not',         # EQUALS_NOT
    4:  'iequals_not',        # IEQUALS_NOT
    5:  'contains',           # CONTAINS
    6:  'icontains',          # ICONTAINS
    7:  'contains_not',       # CONTAINS_NOT
    8:  'icontains_not',      # ICONTAINS_NOT
    9:  'gt',                 # GT
    10: 'gte',                # GTE
    11: 'lt',                 # LT
    12: 'lte',                # LTE
    13: 'startswith',         # STARTSWITH
    14: 'istartswith',        # ISTARTSWITH
    15: 'startswith_not',     # STARTSWITH_NOT
    16: 'istartswith_not',    # ISTARTSWITH_NOT
    17: 'endswith',           # ENDSWITH
    18: 'iendswith',          # IENDSWITH
    19: 'endswith_not',       # ENDSWITH_NOT
    20: 'iendswith_not',      # IENDSWITH_NOT
    21: 'isempty',            # ISEMPTY
    22: 'range',              # RANGE
    23: 'currentyear',        # CURRENTYEAR
    24: 'currentyear_plus',   # CURRENTYEAR_PLUS
    25: 'currentyear_minus',  # CURRENTYEAR_MINUS
}


def convert_filter(apps, schema_editor):
    for cond in apps.get_model('creme_core', 'EntityFilterCondition').objects.filter(
        type__in=[
            5,   # RegularFieldConditionHandler
            20,  # CustomFieldConditionHandler
        ],
    ):
        value = cond.value
        value['operator'] = operators_map[value['operator']]
        cond.value = value
        cond.save()


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
        #         "value": {"operator": 1, "values": [true]}
        #       },
        #       {...}, ...
        #     ]
        #   }, {...}, ...
        # ]
        all_conditions = wf.json_conditions
        changed = False
        for source_conditions in all_conditions:
            for cond in source_conditions['conditions']:
                if cond['type'] in (
                    5,   # RegularFieldConditionHandler
                    20,  # CustomFieldConditionHandler
                ):
                    value = cond['value']
                    value['operator'] = operators_map[value['operator']]
                    changed = True

        if changed:
            wf.json_conditions = all_conditions
            wf.save()


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0187_v3_0__clean_roles_data'),
    ]

    operations = [
        migrations.RunPython(convert_filter),
        migrations.RunPython(convert_workflow),
    ]
