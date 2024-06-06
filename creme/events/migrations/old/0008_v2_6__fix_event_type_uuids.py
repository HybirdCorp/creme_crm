from django.db import migrations

IDS_TO_UUIDS = [
    (1, 'd4928cbc-6afd-40bf-9d07-815b8b920b39'),  # Show
    (2, '254fda4f-1a01-47e1-b5aa-a1b2d4ef2890'),  # Conference
    (3, 'b520fe79-98f4-4362-8293-b4febd46c9df'),  # Breakfast
    (4, '42c72e13-9f47-4ea8-bd9b-0a0764ceea19'),  # Brunch
]


def fix_uuids(apps, schema_editor):
    filter_etype = apps.get_model('events', 'EventType').objects.filter
    count = 0

    for etype_id, etype_uuid in IDS_TO_UUIDS:
        etype = filter_etype(id=etype_id).first()

        if etype is not None:
            old_uuid = str(etype.uuid)
            if old_uuid != etype_uuid:
                etype.extra_data['old_uuid'] = old_uuid
                etype.uuid = etype_uuid
                etype.save()

                count += 1

    if count:
        print(
            f'The UUID of {count} "EventType" have been modified '
            f'(old ones are stored in meta_data).'
        )


class Migration(migrations.Migration):
    dependencies = [
        ('events', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(fix_uuids),
    ]
