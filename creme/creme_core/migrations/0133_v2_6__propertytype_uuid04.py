from json import dumps as json_dump
from json import loads as json_load
# from uuid import uuid4
from uuid import UUID

from django.db import migrations

from creme.creme_core.core.paginator import FlowPaginator


# ---
def copy_ptypes(apps, schema_editor):
    get_ct = apps.get_model('contenttypes', 'ContentType').objects.get
    get_or_create_type = apps.get_model('creme_core', 'CremePropertyType').objects.get_or_create

    for old_ptype in apps.get_model('creme_core', 'OldCremePropertyType').objects.all():
        app_label = old_ptype.id.split('-', 1)[0]

        ptype = get_or_create_type(
            old_id=old_ptype.id,
            defaults={
                # 'uuid': uuid4(),
                'app_label': app_label if app_label not in ('creme_core', 'creme_config') else '',
                'text': old_ptype.text,
                'is_custom': old_ptype.is_custom,
                'is_copiable': old_ptype.is_copiable,
                'enabled': old_ptype.enabled,
            },
        )[0]
        if old_ptype.subject_ctypes_bk:
            ptype.subject_ctypes.set([
                get_ct(id=int(ct_id)) for ct_id in old_ptype.subject_ctypes_bk.split(',')
            ])

# ---
def fill_properties(apps, schema_editor):
    filter_properties = apps.get_model('creme_core', 'CremeProperty').objects.filter

    for ptype in apps.get_model('creme_core', 'CremePropertyType').objects.all():
        filter_properties(old_type_id=ptype.old_id).update(type=ptype)


def fill_relation_types(apps, schema_editor):
    get_ptype = apps.get_model('creme_core', 'CremePropertyType').objects.get

    for rtype in apps.get_model('creme_core', 'RelationType').objects.exclude(
        subject_properties_bk='', subject_forbidden_properties_bk='',
    ):
        if rtype.subject_properties_bk:
            rtype.subject_properties.set([
                get_ptype(old_id=old_ptype_id)
                for old_ptype_id in rtype.subject_properties_bk.split(',')
            ])

        if rtype.subject_forbidden_properties_bk:
            rtype.subject_forbidden_properties.set([
                get_ptype(old_id=old_ptype_id)
                for old_ptype_id in rtype.subject_forbidden_properties_bk.split(',')
            ])


# -----
def convert_filter_conditions(apps, schema_editor):
    get_ptype = apps.get_model('creme_core', 'CremePropertyType').objects.get

    for condition in apps.get_model('creme_core', 'EntityFilterCondition').objects.filter(
        type=15, # NB: PropertyConditionHandler.type_id
    ):
        # We avoid already converted conditions to make this code re-runnable
        # (even if it's probably a bad idea to re-run after an error....)
        try:
            UUID(condition.name)
        except ValueError:
            condition.name = str(get_ptype(old_id=condition.name).uuid)
            condition.save()


# -----
# See models.history
TYPE_PROP_ADD = 5
TYPE_PROP_DEL = 13

def convert_history_lines(apps, schema_editor):
    filter_ptype = apps.get_model('creme_core', 'CremePropertyType').objects.filter

    for page in FlowPaginator(
        queryset=apps.get_model('creme_core', 'HistoryLine').objects.filter(
            type__in=(TYPE_PROP_ADD, TYPE_PROP_DEL),
        ),
        key='id',
        per_page=256,
    ).pages():
        for hline in page.object_list:
            # NB: format is ["My entity", 'app_label-my_ptype_id']
            value = json_load(hline.value)
            # old_ptype_id = value[1]
            line_ptype_id = value[1]

            # We avoid already converted lines to make this code re-runnable
            # (even if it's probably a bad idea to re-run after an error...)
            # try:
            #     UUID(old_ptype_id)
            # except ValueError:
            if not isinstance(line_ptype_id, int):
                # ptype = filter_ptype(old_id=old_ptype_id).first()
                ptype = filter_ptype(old_id=line_ptype_id).first()

                hline.value = json_dump([value[0], (0 if ptype is None else ptype.id)])
                hline.save()


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0132_v2_6__propertytype_uuid03'),
    ]

    operations = [
        migrations.RunPython(copy_ptypes),
        migrations.RunPython(fill_properties),
        migrations.RunPython(fill_relation_types),
        migrations.RunPython(convert_filter_conditions),
        migrations.RunPython(convert_history_lines),
    ]
