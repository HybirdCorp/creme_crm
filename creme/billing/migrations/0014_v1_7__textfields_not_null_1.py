# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations


CREDIT_NOTE_FIELDS   = ['comment']
INVOICE_FIELDS       = ['comment']
QUOTE_FIELDS         = ['comment']
SALES_ORDER_FIELDS   = ['comment']
TEMPLATE_BASE_FIELDS = ['comment']

PRODUCT_LINE_FIELDS = ['comment']
SERVICE_LINE_FIELDS = ['comment']

ADDITIONAL_INFO_FIELDS = ['description']
PAYMENT_INFO_FIELDS = ['bic']  # Arg the field was still nullable...
PAYMENT_TERMS_FIELDS = ['description']


def fill_none_strings(apps, schema_editor):
    def migrate_model(name, fields):
        manager = apps.get_model('billing', name).objects

        for field_name in fields:
            manager.filter(**{field_name: None}).update(**{field_name: ''})

    def migrate_swappable_model(setting_model, name, fields):
        if setting_model == 'billing.%s' % name:
            migrate_model(name, fields)

    migrate_model('AdditionalInformation', ADDITIONAL_INFO_FIELDS)
    migrate_model('PaymentInformation',    PAYMENT_INFO_FIELDS)
    migrate_model('PaymentTerms',          PAYMENT_TERMS_FIELDS)

    migrate_swappable_model(settings.BILLING_CREDIT_NOTE_MODEL,   'CreditNote',   CREDIT_NOTE_FIELDS)
    migrate_swappable_model(settings.BILLING_INVOICE_MODEL,       'Invoice',      INVOICE_FIELDS)
    migrate_swappable_model(settings.BILLING_QUOTE_MODEL,         'Quote',        QUOTE_FIELDS)
    migrate_swappable_model(settings.BILLING_SALES_ORDER_MODEL,   'SalesOrder',   SALES_ORDER_FIELDS)
    migrate_swappable_model(settings.BILLING_TEMPLATE_BASE_MODEL, 'TemplateBase', TEMPLATE_BASE_FIELDS)

    migrate_swappable_model(settings.BILLING_PRODUCT_LINE_MODEL,  'ProductLine',  PRODUCT_LINE_FIELDS)
    migrate_swappable_model(settings.BILLING_SERVICE_LINE_MODEL,  'ServiceLine',  SERVICE_LINE_FIELDS)


class Migration(migrations.Migration):
    dependencies = [
        ('billing', '0013_v1_7__charfields_not_null_2'),
    ]

    operations = [
        migrations.RunPython(fill_none_strings),
    ]
