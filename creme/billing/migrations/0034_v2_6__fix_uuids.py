from django.db import migrations

BILLING_PAYMENTTERMS_UUIDS = [
    (1, '86b76130-4cac-4337-95ff-3e9021329956'),  # Deposit
]

BILLING_CREDITNOTESTATUS_UUIDS = [
    (1, '57191226-8ece-4a7d-bb5f-1b9635f41d9b'),  # Draft
    (2, '42263776-44e0-4b63-b330-9a0237ab37c8'),  # Issued
    (3, '8fc73f0e-a427-4a07-b4f3-ae0b3eca9469'),  # Consumed
    (4, '0eee82dd-fb06-4de0-acf9-4d1d4b970399'),  # Out of date
]

BILLING_INVOICESTATUS_UUIDS = [
    (1, '1bbb7c7e-610f-4366-b3de-b92d63c9cf23'),  # Draft
    (2, 'cc1209bb-e8a2-40bb-9361-4230d9e27bf2'),  # To be sent
    (3, 'b8ed248b-5785-47ba-90d0-094ac9f813c7'),  # Sent
    (4, '017e8734-533d-4fc7-b355-c091748ccb34'),  # Resulted
    (5, '0d8da787-394c-4735-8cad-5eb3a2382415'),  # Partly resulted
    (6, '134ed1ba-efce-4984-baae-dae06fa27096'),  # Collection
    (7, 'b5b256bd-6205-4f67-af3b-eb76b47e97fa'),  # Resulted collection
    (8, 'b85ad6ce-9479-4c70-9241-97c03774e521'),  # Canceled
]

BILLING_QUOTESTATUS_UUIDS = [
    (1, '9128fed1-e87d-477b-aa94-3d220f724f05'),  # Pending
    (2, 'aa5b25ec-ea70-470f-91a6-402dffe933a8'),  # Accepted
    (3, '7739a6ac-64a7-4f40-a04d-39a382b08d50'),  # Rejected
    (4, '9571e8bb-7a50-4453-a037-de829e189952'),  # Created
]

BILLING_SALESORDERSTATUS_UUIDS = [
    (1, 'bebdab5a-0281-4b34-a257-26602a19e320'),  # Issued
    (2, '717ac4a7-97f8-4002-a555-544e4427191a'),  # Accepted
    (3, 'a91aa135-b075-4a81-a06b-dd1839954a71'),  # Rejected
    (4, 'ee4dd8f7-557f-46d8-8ed2-74c256875b84'),  # Created
]

BILLING_SETTLEMENTTERMS_UUIDS = [
    (1, '5d5db3d9-8af9-450a-9daa-67e78fae82f8'),  # 30 days
    (2, '36590d27-bf69-43fc-bdb1-d3b13d1fac8e'),  # Cash
    (3, '2d0540fa-8be0-474c-ae97-70d721d17ee3'),  # 45 days
    (4, '3766296a-98ea-4341-a305-30e551d92550'),  # 60 days
    (5, 'ad9152cb-bcb4-43ff-ba15-4b8d90557f23'),  # 30 days, end month the 10
]

BILLING_ADDITIONALINFORMATION_UUIDS = [
    (1, '1c3c5157-1a42-4b88-9b78-de15b41bdd96'),  # Trainer accreditation
]

def _fix_uuids(apps, model_name, ids_to_uuids):
    filter_instances = apps.get_model('billing', model_name).objects.filter
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


def fix_payment_terms_uuids(apps, schema_editor):
    _fix_uuids(
        apps,
        model_name='PaymentTerms',
        ids_to_uuids=BILLING_PAYMENTTERMS_UUIDS,
    )

def fix_cnote_statuses_uuids(apps, schema_editor):
    _fix_uuids(
        apps,
        model_name='CreditNoteStatus',
        ids_to_uuids=BILLING_CREDITNOTESTATUS_UUIDS,
    )

def fix_invoice_statuses_uuids(apps, schema_editor):
    _fix_uuids(
        apps,
        model_name='InvoiceStatus',
        ids_to_uuids=BILLING_INVOICESTATUS_UUIDS,
    )

def fix_quote_statuses_uuids(apps, schema_editor):
    _fix_uuids(
        apps,
        model_name='QuoteStatus',
        ids_to_uuids=BILLING_QUOTESTATUS_UUIDS,
    )

def fix_order_statuses_uuids(apps, schema_editor):
    _fix_uuids(
        apps,
        model_name='SalesOrderStatus',
        ids_to_uuids=BILLING_SALESORDERSTATUS_UUIDS,
    )

def fix_settlement_uuids(apps, schema_editor):
    _fix_uuids(
        apps,
        model_name='SettlementTerms',
        ids_to_uuids=BILLING_SETTLEMENTTERMS_UUIDS,
    )

def fix_additional_uuids(apps, schema_editor):
    _fix_uuids(
        apps,
        model_name='AdditionalInformation',
        ids_to_uuids=BILLING_ADDITIONALINFORMATION_UUIDS,
    )


class Migration(migrations.Migration):
    dependencies = [
        ('billing', '0033_v2_6__statuses_is_default02'),
    ]

    operations = [
        migrations.RunPython(fix_payment_terms_uuids),
        migrations.RunPython(fix_cnote_statuses_uuids),
        migrations.RunPython(fix_invoice_statuses_uuids),
        migrations.RunPython(fix_quote_statuses_uuids),
        migrations.RunPython(fix_order_statuses_uuids),
        migrations.RunPython(fix_settlement_uuids),
        migrations.RunPython(fix_additional_uuids),
    ]
