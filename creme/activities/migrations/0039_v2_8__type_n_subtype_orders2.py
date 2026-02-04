from django.db import migrations

from creme.activities import constants


def generate_orders(apps, schema_editor):
    ActivitySubType = apps.get_model('activities', 'ActivitySubType')
    default_sub_uuids = {
        constants.UUID_TYPE_MEETING:   constants.UUID_SUBTYPE_MEETING_MEETING,
        constants.UUID_TYPE_PHONECALL: constants.UUID_SUBTYPE_PHONECALL_OUTGOING,
    }

    for atype_order, atype in enumerate(
        apps.get_model('activities', 'ActivityType').objects.order_by('name'),
        start=1,
    ):
        atype.order = atype_order
        atype.save()

        sub_types = {
            str(sub_type.uuid): sub_type
            for sub_type in ActivitySubType.objects.filter(type_id=atype.id).order_by('name')
        }
        start_order = 1
        default_uuid = default_sub_uuids.get(str(atype.uuid))

        if default_uuid:
            default_subtype = sub_types.pop(default_uuid, None)

            if default_subtype:
                default_subtype.order = 1
                default_subtype.save()

                start_order = 2

        for subtype_order, subtype in enumerate(sub_types.values(), start=start_order):
            subtype.order = subtype_order
            subtype.save()


class Migration(migrations.Migration):
    dependencies = [
        ('activities', '0038_v2_8__type_n_subtype_orders1'),
    ]

    operations = [
        migrations.RunPython(generate_orders),
    ]
