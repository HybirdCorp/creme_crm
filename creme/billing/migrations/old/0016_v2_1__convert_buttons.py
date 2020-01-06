# -*- coding: utf-8 -*-

from django.db import migrations


def add_convertion_buttons(apps, schema_editor):
    from creme.billing import buttons

    ContentType = apps.get_model('contenttypes', 'ContentType')
    ButtonMenuItem = apps.get_model('creme_core', 'ButtonMenuItem')

    ct_quote = ContentType.objects.filter(app_label='billing', model='quote').first()
    ct_order = ContentType.objects.filter(app_label='billing', model='salesorder').first()

    if ct_order is None or ct_quote is None or not ButtonMenuItem.objects.exists():
        return

    ButtonMenuItem.objects.create(
        pk='billing-convert_quote_to_invoice',
        content_type_id=ct_quote.pk,
        button_id=buttons.ConvertToInvoiceButton.id_,
        order=0,
    )
    ButtonMenuItem.objects.create(
        pk='billing-convert_quote_to_salesorder',
        content_type_id=ct_quote.pk,
        button_id=buttons.ConvertToSalesOrderButton.id_,
        order=1,
    )

    ButtonMenuItem.objects.create(
        pk='billing-convert_salesorder_to_invoice',
        content_type_id=ct_order.pk,
        button_id=buttons.ConvertToInvoiceButton.id_,
        order=0,
    )


class Migration(migrations.Migration):
    dependencies = [
        ('billing', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(add_convertion_buttons),
    ]
