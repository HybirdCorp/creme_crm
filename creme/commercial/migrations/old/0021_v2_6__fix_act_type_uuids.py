from django.db import migrations

IDS_TO_UUIDS = [
    (1, 'e443e7f0-df22-4f4c-9bc8-7f718867e3d1'),
    (2, '2937497e-05b2-4790-8fa9-7f2a05dbfee0'),
    (3, '4cfcefd1-3140-4e9f-a6f5-ce7de1e08f51'),
]


def fix_uuids(apps, schema_editor):
    filter_instances = apps.get_model('commercial', 'ActType').objects.filter
    count = 0

    for old_id, new_uuid in IDS_TO_UUIDS:
        instance = filter_instances(id=old_id).first()

        if instance is not None:
            old_uuid = str(instance.uuid)

            if old_uuid != new_uuid:
                instance.extra_data['old_uuid'] = old_uuid
                instance.uuid = new_uuid
                instance.save()

                count += 1

    if count:
        print(
            f'The UUID of {count} "ActType" have been modified '
            f'(old ones are stored in meta_data).'
        )


class Migration(migrations.Migration):

    dependencies = [
        ('commercial', '0020_v2_6__ptype_uuid05'),
    ]

    operations = [
        migrations.RunPython(fix_uuids),
    ]
