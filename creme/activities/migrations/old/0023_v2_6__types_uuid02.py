from json import dumps as json_dump
from json import loads as json_load
from uuid import uuid4

from django.db import migrations
from django.db.models.query_utils import Q

from creme.activities import constants
from creme.creme_core.core.paginator import FlowPaginator

TYPES_ID_2_UUID = {
    'activities-activitytype_indispo':   constants.UUID_TYPE_UNAVAILABILITY,
    'activities-activitytype_task':      constants.UUID_TYPE_TASK,
    'activities-activitytype_meeting':   constants.UUID_TYPE_MEETING,
    'activities-activitytype_phonecall': constants.UUID_TYPE_PHONECALL,
    'activities-activitytype_gathering': constants.UUID_TYPE_GATHERING,
    'activities-activitytype_show':      constants.UUID_TYPE_SHOW,
    'activities-activitytype_demo':      constants.UUID_TYPE_DEMO,
}
SUBTYPES_ID_2_UUID = {
    'activities-activitysubtype_unavailability': constants.UUID_SUBTYPE_UNAVAILABILITY,

    'activities-activitysubtype_meeting':       constants.UUID_SUBTYPE_MEETING_MEETING,
    'activities-activitysubtype_qualification': constants.UUID_SUBTYPE_MEETING_QUALIFICATION,
    'activities-activitysubtype_revival':       constants.UUID_SUBTYPE_MEETING_REVIVAL,
    'activities-activitysubtype_network':       constants.UUID_SUBTYPE_MEETING_NETWORK,
    'activities-activitysubtype_other':         constants.UUID_SUBTYPE_MEETING_OTHER,

    'activities-activitysubtype_incoming':   constants.UUID_SUBTYPE_PHONECALL_INCOMING,
    'activities-activitysubtype_outgoing':   constants.UUID_SUBTYPE_PHONECALL_OUTGOING,
    'activities-activitysubtype_conference': constants.UUID_SUBTYPE_PHONECALL_CONFERENCE,
    'activities-activitysubtype_failed':     constants.UUID_SUBTYPE_PHONECALL_FAILED,

    'activities-activitysubtype_holidays': 'd0408f78-77ba-4c49-9fa7-fc1e3455554e',
    'activities-activitysubtype_ill':      '09baec7a-b0ba-4c03-8981-84fc066d2970',

    'activities-activitysubtype_task': '767b94e1-b366-4b97-8755-d719b268e402',

    'activities-activitysubtype_gathering':          '75b957a2-4fe7-4b98-8493-3f95e43a4968',
    'activities-activitysubtype_gathering_team':     '2147569e-7bc4-4b79-8760-844dc568c422',
    'activities-activitysubtype_gathering_internal': 'e4ff08c8-80df-4528-bcc1-4f9d20c6fe61',
    'activities-activitysubtype_gathering_on_site':  '1c626935-d47a-4d9b-af4b-b90b8a71fc77',
    'activities-activitysubtype_gathering_remote':   '8f003f06-f1ea-456e-90f3-82e8b8ef7424',
    'activities-activitysubtype_gathering_outside':  'bc001a5c-eb90-4a3c-b703-afe347d3bf34',

    'activities-activitysubtype_show_exhibitor': 'b75a663c-af2e-4440-89b3-2a75410cd55b',
    'activities-activitysubtype_show_visitor':   '591b34b3-4226-48d4-a74d-d94665190b44',

    'activities-activitysubtype_demo':                 'c32a94c7-8a2a-4589-8b0d-6764c63fb659',
    'activities-activitysubtype_demo_on_site':         '247902ed-05dd-4ba6-9cbd-ea43b7c996eb',
    'activities-activitysubtype_demo_outside':         'e22a2e5d-4349-4d44-bd77-21b1a10816d5',
    'activities-activitysubtype_demo_videoconference': '3faf21bf-80b4-4182-b975-8146db2fb68b',
}

# ---
def copy_types(apps, schema_editor):
    get_or_create_type = apps.get_model('activities', 'ActivityType').objects.get_or_create

    for old_type in apps.get_model('activities', 'OldActivityType').objects.all():
        get_or_create_type(
            old_id=old_type.id,
            defaults={
                'uuid': TYPES_ID_2_UUID.get(old_type.id) or uuid4(),
                'name': old_type.name,
                'default_day_duration':  old_type.default_day_duration,
                'default_hour_duration': old_type.default_hour_duration,
                'is_custom': old_type.is_custom,
                'extra_data': old_type.extra_data,
            },
        )


def copy_sub_types(apps, schema_editor):
    get_type = apps.get_model('activities', 'ActivityType').objects.get
    get_or_create_subtype = apps.get_model('activities', 'ActivitySubType').objects.get_or_create

    for old_sub_type in apps.get_model('activities', 'OldActivitySubType').objects.all():
        get_or_create_subtype(
            old_id=old_sub_type.id,
            defaults={
                'uuid': SUBTYPES_ID_2_UUID.get(old_sub_type.id) or uuid4(),
                'name': old_sub_type.name,
                'type': get_type(old_id=old_sub_type.type_id),
                'is_custom': old_sub_type.is_custom,
                'extra_data': old_sub_type.extra_data,
            },
        )


def fill_activities(apps, schema_editor):
    filter_activities = apps.get_model('activities', 'Activity').objects.filter

    for sub_type in apps.get_model('activities', 'ActivitySubType').objects.all():
        filter_activities(old_sub_type_id=sub_type.old_id).update(
            sub_type=sub_type,
            type_id=sub_type.type_id,
        )

# -----
REGULAR_TYPE_ID = 5  # NB: RegularFieldConditionHandler.type_id


# TODO: make re-runnable?
def convert_filter_conditions(apps, schema_editor):
    activity_ct = apps.get_model('contenttypes', 'ContentType').objects.filter(
        app_label='activities', model='activity',
    ).first()
    if activity_ct is None:
        return

    EntityFilterCondition = apps.get_model('creme_core', 'EntityFilterCondition')
    get_type = apps.get_model('activities', 'ActivityType').objects.get

    for condition in EntityFilterCondition.objects.filter(
        filter__entity_type=activity_ct, type=REGULAR_TYPE_ID, name='type',
    ):
        value = condition.value
        value['values'] = [str(get_type(old_id=old_id).id) for old_id in value['values']]
        condition.value = value
        condition.save()

    get_sub_type = apps.get_model('activities', 'ActivitySubType').objects.get
    for condition in EntityFilterCondition.objects.filter(
        filter__entity_type=activity_ct, type=REGULAR_TYPE_ID, name='sub_type',
    ):
        value = condition.value
        value['values'] = [str(get_sub_type(old_id=old_id).id) for old_id in value['values']]
        condition.value = value
        condition.save()


# -----
# See models.history
TYPE_EDITION = 2

# TODO: make re-runnable?
def convert_history_lines(apps, schema_editor):
    activity_ct = apps.get_model('contenttypes', 'ContentType').objects.filter(
        app_label='activities', model='activity',
    ).first()
    if activity_ct is None:
        return

    ActivityType    = apps.get_model('activities', 'ActivityType')
    ActivitySubType = apps.get_model('activities', 'ActivitySubType')

    def new_ids(model, old_ids):
        for old_id in old_ids:
            instance = model.objects.filter(old_id=old_id).first()
            yield 0 if instance is None else instance.id

    for page in FlowPaginator(
        queryset=apps.get_model('creme_core', 'HistoryLine').objects.filter(
            type=TYPE_EDITION, entity_ctype=activity_ct,
        ).filter(Q(value__contains='["type"') | Q(value__contains='["sub_type"')),
        key='id',
        per_page=256,
    ).pages():
        for hline in page.object_list:
            # NB: "type"/"sub_type" could be the name of the entity...
            save = False
            # NB: format is ["My entity", ["field1", "old value", "new_value"], ["field2", ...], ...]
            value = json_load(hline.value)

            modifications = []
            for old_mod in value[1:]:
                field_name = old_mod[0]
                if field_name == "type":
                    modifications.append([
                        field_name,
                        *new_ids(ActivityType, old_mod[1:])
                    ])

                    save = True
                elif field_name == "sub_type":
                    modifications.append([
                        field_name,
                        *new_ids(ActivitySubType, old_mod[1:])
                    ])

                    save = True
                else:
                    modifications.append(old_mod)

            if save:
                hline.value = json_dump([value[0], *modifications])
                hline.save()


# -----
class Migration(migrations.Migration):
    dependencies = [
        ('activities', '0022_v2_6__types_uuid01'),
        ('creme_core', '0129_v2_6__filtercondition_jsonfield02'),
    ]

    operations = [
        migrations.RunPython(copy_types),
        migrations.RunPython(copy_sub_types),
        migrations.RunPython(fill_activities),
        migrations.RunPython(convert_filter_conditions),
        migrations.RunPython(convert_history_lines),
    ]
