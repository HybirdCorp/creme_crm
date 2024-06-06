from django.db import migrations


def set_default_statuses(apps, schema_editor):
    for model_name in (
        'InvoiceStatus', 'QuoteStatus', 'CreditNoteStatus', 'SalesOrderStatus',
    ):
        status = apps.get_model('billing', model_name).objects.order_by('id').first()
        if status:
            status.is_default = True
            status.save()

    # DEFAULT_INVOICE_STATUS = 2
    status = apps.get_model('billing', 'InvoiceStatus').objects.filter(id=2).first()
    if status:
        status.is_validated = True
        status.save()


class Migration(migrations.Migration):
    dependencies = [
        ('billing', '0032_v2_6__statuses_is_default01'),
    ]

    operations = [
        migrations.RunPython(set_default_statuses),
    ]
