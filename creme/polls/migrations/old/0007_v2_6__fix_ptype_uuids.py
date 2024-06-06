from django.db import migrations

IDS_TO_UUIDS = [
    (1, '90d3d792-4354-43d2-8da2-9abf7cdd1421'),  # Survey
    (2, 'f3568c0a-ba44-485d-b4f3-88dac5c9477b'),  # Monitoring
    (3, '3b50033a-b77c-43e4-88ae-145e433dc1ca'),  # Assessment
]


def fix_uuids(apps, schema_editor):
    filter_ptype = apps.get_model('polls', 'PollType').objects.filter
    count = 0

    for ptype_id, ptype_uuid in IDS_TO_UUIDS:
        ptype = filter_ptype(id=ptype_id).first()

        if ptype is not None:
            old_uuid = str(ptype.uuid)

            if old_uuid != ptype_uuid:
                ptype.extra_data['old_uuid'] = old_uuid
                ptype.uuid = ptype_uuid
                ptype.save()

                count += 1

    if count:
        print(
            f'The UUID of {count} "PollType" have been modified '
            f'(old ones are stored in meta_data).'
        )


class Migration(migrations.Migration):
    dependencies = [
        ('polls', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(fix_uuids),
    ]
