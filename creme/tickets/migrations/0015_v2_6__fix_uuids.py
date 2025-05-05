from django.db import migrations

TICKETS_STATUS_UUIDS = [
    (1, '9c70ade9-1d84-41b4-8b80-73090590de20'),
    (2, '7cb4d6d8-8fc8-4500-9941-becff6ce0dfc'),
    (3, '367377a2-cacc-490c-8996-2170408ee202'),
    (4, '004be181-1dac-4b53-9bb0-8b6dc6435c3d'),
    (5, 'cfea0016-12f8-4a81-b659-b4cf07cdda0e'),
]

TICKETS_PRIORITY_UUIDS = [
    (1, '87599d36-8133-41b7-a382-399d5e96b160'),
    (2, '816cefa7-2f30-46a6-8baa-92e4647f44d3'),
    (3, '42c39215-cf78-4d0b-b00b-b54a6680f71a'),
    (4, '69bdbe35-cf99-4168-abb3-389aab6b7313'),
    (5, 'd2dba4cb-382c-4d94-8306-4ec739f03144'),
]

TICKETS_CRITICITY_UUIDS = [
    (1, '368a6b62-c66e-4286-b841-1062f59133c9'),
    (2, '1aa05ca4-68ec-4068-ac3b-b9ddffaeb0aa'),
    (3, 'e5a2a80e-36e8-49fd-8b2b-e802ccd4090c'),
    (4, '9937c865-d0e7-4f33-92f3-600814e293ad'),
    (5, '8e509e5e-8bd6-4cd0-8f96-5c129f0a875d'),
    (6, '3bd07632-f3ad-415e-bb33-95c723e46aa5'),
]

def _fix_uuids(apps, model_name, ids_to_uuids):
    filter_instances = apps.get_model('tickets', model_name).objects.filter
    count = 0

    for old_id, new_uuid in ids_to_uuids:
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
            f'The UUID of {count} "{model_name}" have been modified '
            f'(old ones are stored in meta_data).'
        )

def fix_statuses_uuids(apps, schema_editor):
    _fix_uuids(
        apps,
        model_name='Status',
        ids_to_uuids=TICKETS_STATUS_UUIDS,
    )

def fix_priorities_uuids(apps, schema_editor):
    _fix_uuids(
        apps,
        model_name='Priority',
        ids_to_uuids=TICKETS_PRIORITY_UUIDS,
    )

def fix_criticality_uuids(apps, schema_editor):
    _fix_uuids(
        apps,
        model_name='Criticity',
        ids_to_uuids=TICKETS_CRITICITY_UUIDS,
    )


class Migration(migrations.Migration):
    dependencies = [
        ('tickets', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(fix_statuses_uuids),
        migrations.RunPython(fix_priorities_uuids),
        migrations.RunPython(fix_criticality_uuids),
    ]
