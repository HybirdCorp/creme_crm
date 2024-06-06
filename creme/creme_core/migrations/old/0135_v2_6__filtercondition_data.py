from django.db import migrations

from creme.creme_core.core.entity_filter import condition_handler


def fix_conditions(apps, schema_editor):
    get_ct = apps.get_model('contenttypes', 'ContentType').objects.get
    get_cfield = apps.get_model('creme_core', 'CustomField').objects.get
    get_entity = apps.get_model('creme_core', 'CremeEntity').objects.get
    filter_conds = apps.get_model('creme_core', 'EntityFilterCondition').objects.filter

    for cond in filter_conds(
        type__in=(
            condition_handler.CustomFieldConditionHandler.type_id,
            condition_handler.DateCustomFieldConditionHandler.type_id,
        ),
    ):
        if cond.name.isdigit():  # To make this migration re-runnable even without transaction...
            cond.name = str(get_cfield(id=int(cond.name)).uuid)
            cond.save()

    for cond in filter_conds(type=condition_handler.RelationConditionHandler.type_id):
        value: dict = cond.value
        save = False

        entity_id = value.pop('entity_id', None)
        if entity_id is not None:
            save = True
            value['entity'] = str(get_entity(id=entity_id).uuid)

        ct_id = value.pop('ct_id', None)
        if ct_id is not None:
            save = True
            ct = get_ct(id=ct_id)
            value['ct'] = f'{ct.app_label}.{ct.model}'

        if save:
            cond.value = value
            cond.save()


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0134_v2_6__propertytype_uuid05'),
    ]

    operations = [
        migrations.RunPython(fix_conditions),
    ]
