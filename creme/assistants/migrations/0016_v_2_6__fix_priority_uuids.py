from django.db import migrations

IDS_TO_UUIDS = [
    (1, 'd9dba2d3-18cf-4166-9bd7-6a9fa299e9e1'),  # IMPORTANT
    (2, '16445980-4abe-409c-8c45-f2f4f9bfc945'),  # VERY_IMPORTANT
    (3, '2e4eb53f-e686-42e5-8352-4d3c0ef6c19e'),  # NOT_IMPORTANT
]


def fix_uuids(apps, schema_editor):
    filter_priority = apps.get_model('assistants', 'UserMessagePriority').objects.filter
    count = 0

    for prio_id, prio_uuid in IDS_TO_UUIDS:
        priority = filter_priority(id=prio_id).first()
        if priority is not None:
            old_uuid = str(priority.uuid)
            if old_uuid != prio_uuid:
                priority.extra_data['old_uuid'] = old_uuid
                priority.uuid = prio_uuid
                priority.save()

                count += 1

    if count:
        print(
            f'The UUID of {count} "Priority" have been modified '
            f'(old ones are stored in meta_data).'
        )


class Migration(migrations.Migration):
    dependencies = [
        ('assistants', '0015_v2_6__remove_usermessage_email_sent'),
    ]

    operations = [
        migrations.RunPython(fix_uuids),
    ]
