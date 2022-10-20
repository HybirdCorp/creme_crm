import json

from django.conf import settings
from django.db import migrations
from django.utils.translation import activate
from django.utils.translation import gettext_lazy as _

from creme.activities import constants

TYPES_INFO = {
    constants.ACTIVITYTYPE_INDISPO:   ('activities-activitysubtype_unavailability', _('Unavailability'), False),
    constants.ACTIVITYTYPE_TASK:      ('activities-activitysubtype_task',           _('Task'),           True),
    constants.ACTIVITYTYPE_GATHERING: ('activities-activitysubtype_gathering',      _('Gathering'),      True),
    constants.ACTIVITYTYPE_SHOW:      ('activities-activitysubtype_show',           _('Show'),           True),
    constants.ACTIVITYTYPE_DEMO:      ('activities-activitysubtype_demo',           _('Demonstration'),  True),
}


def fill_sub_types(apps, schema_editor):
    if settings.ACTIVITIES_ACTIVITY_MODEL != 'activities.Activity':
        return

    Activity = apps.get_model('activities', 'Activity')

    type_ids = Activity.objects.filter(
        sub_type=None,
    ).values_list('type_id', flat=True).distinct()
    if not type_ids:
        return

    activate(settings.LANGUAGE_CODE)

    ActivityType = apps.get_model('activities', 'ActivityType')
    ActivitySubType = apps.get_model('activities', 'ActivitySubType')

    pk_prefix = 'migrations-0018_v2_4__not_null_subtype01-'

    for type_id in type_ids:
        type_info = TYPES_INFO.get(type_id)
        if type_info:
            pk, name, is_custom = type_info
            sub_type = ActivitySubType.objects.get_or_create(
                pk=pk,
                defaults={'name': str(name), 'type_id': type_id, 'is_custom': is_custom},
            )[0]
        else:
            # We copy the name of the related type because we cannot create a smart name.
            name = ActivityType.objects.get(id=type_id).name

            sub_type = ActivitySubType.objects.filter(type_id=type_id, name=name).first()
            if sub_type is None:
                number = ActivitySubType.objects.filter(id__startswith=pk_prefix).count() + 1
                sub_type = ActivitySubType.objects.create(
                    id=f'{pk_prefix}{number}',
                    type_id=type_id,
                    name=name,
                    is_custom=True,
                )

        Activity.objects.filter(type_id=type_id, sub_type=None).update(sub_type=sub_type)


def clean_fields_config(apps, schema_editor):
    # The field 'sub_type' is not blank anymore, so it cannot be configured as
    # mandatory (it already is!).
    if settings.ACTIVITIES_ACTIVITY_MODEL != 'activities.Activity':
        return

    ct = apps.get_model('contenttypes', 'ContentType').objects.filter(
        app_label='activities', model='activity',
    ).first()
    if ct is None:
        return

    fconf = apps.get_model('creme_core', 'FieldsConfig').objects.filter(
        content_type=ct,
    ).first()

    if fconf is not None:
        descriptions = json.loads(fconf.raw_descriptions)
        index_to_remove = None
        for i, (field_name, field_info) in enumerate(descriptions):
            if field_name == 'sub_type':
                index_to_remove = i
                break

        if index_to_remove is not None:
            print(
                "Activity.sub_type is now always mandatory, "
                "your fields' configuration is updated."
            )
            descriptions.pop(index_to_remove)

            fconf.raw_descriptions = json.dumps(descriptions)
            fconf.save()


class Migration(migrations.Migration):
    dependencies = [
        ('activities', '0017_v2_4__minion_models03'),
    ]

    operations = [
        migrations.RunPython(fill_sub_types),
        migrations.RunPython(clean_fields_config),
    ]
