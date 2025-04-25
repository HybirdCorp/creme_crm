from django.db import migrations

OPPORTUNITIES_SALESPHASE_UUIDS = [
    (1, '9fc5ff38-b358-4131-b03e-6c1f800bfb08'),  # Forthcoming
    (2, '4445c750-bcec-4fcd-afb2-c9e35a3bf38c'),  # In progress
    (3, 'aa59fcec-2dde-46e1-a362-c30c18386c19'),  # Under negotiation
    (4, '779931a8-a2ed-47b1-96a1-8694452e9905'),  # Abandoned
    (5, 'd8b5429f-89e5-46cc-9e53-5d1a0127f880'),  # Won
    (6, '597d796e-a368-48f0-8dfb-56f16965792b'),  # Lost
]

OPPORTUNITIES_ORIGIN_UUIDS = [
    (1, '814e485e-418a-42d5-a6ef-720aaffee7a0'),  # None
    (2, '96f55fa8-df31-4d64-8f7e-c0b5f1ca0bc6'),  # Web site
    (3, '0e914271-b162-4554-afae-837916378220'),  # Mouth
    (4, '14d5bb2f-5ad7-46ab-a194-59f2bb105b66'),  # Show
    (5, '0f23d337-7a64-4f22-9448-7c0d2df9891b'),  # Direct email
    (6, 'b4e097b9-05c0-4fc9-8c12-bc62cf106046'),  # Direct phone call
    (7, 'c8632a03-4b78-4c00-8e45-7b04bacab2e8'),  # Employee
    (8, '9bb9012f-a4dd-4e4c-8fb8-65c2aaaea789'),  # Partner
    (9, '4b0a0229-cd0d-400d-8fb5-29a1479c41fe'),  # Other
]

def _fix_uuids(apps, model_name, ids_to_uuids):
    filter_instances = apps.get_model('opportunities', model_name).objects.filter
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


def fix_sales_phases_uuids(apps, schema_editor):
    _fix_uuids(
        apps,
        model_name='SalesPhase',
        ids_to_uuids=OPPORTUNITIES_SALESPHASE_UUIDS,
    )


def fix_origins_uuids(apps, schema_editor):
    _fix_uuids(
        apps,
        model_name='Origin',
        ids_to_uuids=OPPORTUNITIES_ORIGIN_UUIDS,
    )


class Migration(migrations.Migration):
    dependencies = [
        ('opportunities', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(fix_sales_phases_uuids),
        migrations.RunPython(fix_origins_uuids),
    ]
