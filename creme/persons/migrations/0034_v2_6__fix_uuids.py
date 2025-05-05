from django.db import migrations

PERSONS_CIVILITY_UUIDS = [
    (1, '7c3867da-af53-43d4-bfcc-75c1c3e5121e'),  # Madam
    (2, '6b84a23d-c4ec-41c1-a35d-e6c0af5af2a0'),  # Miss
    (3, '08e68afd-64aa-4981-a1db-4bde37b08655'),  # Mister
    (4, '547504b3-a886-4837-9170-62f2bc706e7f'),  # N/A
]

PERSONS_POSITION_UUIDS = [
    (1, '1534eb82-f55c-45ef-af2e-4e2d5d68218f'),  # CEO
    (2, '7e10f7f8-730c-45b4-8e81-6b2e4cfbab36'),  # Secretary
    (3, '9669e6a9-4661-4248-bc7c-d675f6e13216'),  # Technician
]

PERSONS_SECTOR_UUIDS = [
    (1, '4995508b-069b-4ad5-a07d-9ae9c17918f2'),  # 'Food Industry
    (2, '06581ce8-e5ab-4875-b18d-b1ae366a9073'),  # Industry
    (3, 'd3d16967-b4e4-4dff-a401-c97ab36fa9a2'),  # Software
    (4, '471ec83d-d7cc-4b51-8ff4-b3b16c339927'),  # Telecom
    (5, '115ecac3-dda1-4388-ad8c-c1d4d6e86214'),  # Restoration
]

PERSONS_LEGALFORM_UUIDS = [
    (1, '0f9ffebf-ae6a-4314-bf78-5ac33c477385'),  # SARL
    (2, '97ec5342-cfcd-47f2-9977-03238a4bb815'),  # Association loi 1901
    (3, '2a18cf05-19bd-47d1-96d0-7dd2ea969e74'),  # SA
    (4, '2085dfac-9714-407c-972b-2256e8472124'),  # SAS
]


PERSONS_STAFFSIZE_UUIDS = [
    (1, '625f5c71-db51-48f7-b548-63360d0b6653'),  # 1 - 5
    (2, '405efcfb-b6cc-4996-8062-b0794d6b718b'),  # 6 - 10
    (3, '57b8a9f0-b672-473a-bc77-db0cd73f4d71'),  # 11 - 50
    (4, 'bab5348c-9a46-4a05-a72e-b94db229f818'),  # 51 - 100
    (5, 'fd1a7587-624f-4cd1-adbc-309e237cfe91'),  # 100 - 500
    (6, 'ca0a585c-a40d-480c-86d0-c9610c93b23b'),  # > 500
]


def _fix_uuids(apps, model_name, ids_to_uuids):
    filter_instances = apps.get_model('persons', model_name).objects.filter
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

def fix_civilities_uuids(apps, schema_editor):
    _fix_uuids(
        apps,
        model_name='Civility',
        ids_to_uuids=PERSONS_CIVILITY_UUIDS,
    )

def fix_positions_uuids(apps, schema_editor):
    _fix_uuids(
        apps,
        model_name='Position',
        ids_to_uuids=PERSONS_POSITION_UUIDS,
    )

def fix_sectors_uuids(apps, schema_editor):
    _fix_uuids(
        apps,
        model_name='Sector',
        ids_to_uuids=PERSONS_SECTOR_UUIDS,
    )


def fix_legal_forms_uuids(apps, schema_editor):
    _fix_uuids(
        apps,
        model_name='LegalForm',
        ids_to_uuids=PERSONS_LEGALFORM_UUIDS,
    )

def fix_staff_sizes_uuids(apps, schema_editor):
    _fix_uuids(
        apps,
        model_name='StaffSize',
        ids_to_uuids=PERSONS_STAFFSIZE_UUIDS,
    )


class Migration(migrations.Migration):
    dependencies = [
        ('persons', '0033_v2_6__is_staff_contact'),
    ]

    operations = [
        migrations.RunPython(fix_civilities_uuids),
        migrations.RunPython(fix_positions_uuids),
        migrations.RunPython(fix_sectors_uuids),
        migrations.RunPython(fix_legal_forms_uuids),
        migrations.RunPython(fix_staff_sizes_uuids),
    ]
