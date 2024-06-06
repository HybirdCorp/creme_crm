from django.db import migrations

IDS_TO_UUIDS = [
    (1, '7efc9a5d-eacd-4be0-afa8-3277256bfcac'),  # STATUS_PLANNED
    (2, '5152460c-18c3-4b8e-a780-ac286294a46e'),  # STATUS_IN_PROGRESS
    (3, '4c7f518b-6bd5-44ea-a867-5e33f50646da'),  # STATUS_DONE
    (4, '98f1990a-049a-4ff9-9a52-957a90e43bbd'),  # STATUS_DELAYED
    (5, '9c23117f-a2eb-4284-8cc2-0c541f87e7ef'),  # STATUS_CANCELLED
]


def fix_uuids(apps, schema_editor):
    filter_status = apps.get_model('activities', 'Status').objects.filter
    count = 0

    for status_id, status_uuid in IDS_TO_UUIDS:
        status = filter_status(id=status_id).first()
        if status is not None:
            old_uuid = str(status.uuid)
            if old_uuid != status_uuid:
                status.extra_data['old_uuid'] = old_uuid
                status.uuid = status_uuid
                status.save()

                count += 1

    if count:
        print(
            f'The UUID of {count} "Status" have been modified '
            f'(old ones are stored in meta_data).'
        )


class Migration(migrations.Migration):
    dependencies = [
        ('activities', '0025_v2_6__calendarconfigitem'),
    ]

    operations = [
        migrations.RunPython(fix_uuids),
    ]
