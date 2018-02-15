# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations


# NB: it seems PostGreSQL does like that we migrate CharFields directly
#     (ie: only '0013_v1_7__charfields_not_null_2.py')

PAYMENT_INFO_FIELDS = ['bank_code', 'counter_code', 'account_number', 'rib_key',
                       'banking_domiciliation', 'iban', 'bic',
                      ]

CREDIT_NOTE_FIELDS   = ['number']
INVOICE_FIELDS       = ['number']
QUOTE_FIELDS         = ['number']
SALES_ORDER_FIELDS   = ['number']
TEMPLATE_BASE_FIELDS = ['number']

PRODUCT_LINE_FIELDS = ['unit']
SERVICE_LINE_FIELDS = ['unit']


def fill_none_strings(apps, schema_editor):
    def migrate_model(name, fields):
        manager = apps.get_model('billing', name).objects

        for field_name in fields:
            manager.filter(**{field_name: None}).update(**{field_name: ''})

    def migrate_swappable_model(setting_model, name, fields):
        if setting_model == 'billing.%s' % name:
            migrate_model(name, fields)

    migrate_model('PaymentInformation', PAYMENT_INFO_FIELDS)

    migrate_swappable_model(settings.BILLING_CREDIT_NOTE_MODEL,   'CreditNote',   CREDIT_NOTE_FIELDS)
    migrate_swappable_model(settings.BILLING_INVOICE_MODEL,       'Invoice',      INVOICE_FIELDS)
    migrate_swappable_model(settings.BILLING_QUOTE_MODEL,         'Quote',        QUOTE_FIELDS)
    migrate_swappable_model(settings.BILLING_SALES_ORDER_MODEL,   'SalesOrder',   SALES_ORDER_FIELDS)
    migrate_swappable_model(settings.BILLING_TEMPLATE_BASE_MODEL, 'TemplateBase', TEMPLATE_BASE_FIELDS)

    migrate_swappable_model(settings.BILLING_PRODUCT_LINE_MODEL,  'ProductLine',  PRODUCT_LINE_FIELDS)
    migrate_swappable_model(settings.BILLING_SERVICE_LINE_MODEL,  'ServiceLine',  SERVICE_LINE_FIELDS)


# Beware: Line.on_the_fly_item is still 'null', but not blank
def replace_empty_strings(apps, schema_editor):
    def migrate_swappable_model(setting_model, name, field_name):
        if setting_model == 'billing.%s' % name:
            apps.get_model('billing', name).objects.filter(**{field_name: ''}) \
                                                   .update(**{field_name: None})

    migrate_swappable_model(settings.BILLING_PRODUCT_LINE_MODEL, 'ProductLine', 'on_the_fly_item')
    migrate_swappable_model(settings.BILLING_SERVICE_LINE_MODEL, 'ServiceLine', 'on_the_fly_item')


class Migration(migrations.Migration):
    dependencies = [
        # ('billing', '0011_v1_6__clean_ctypes'),
        ('billing', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(fill_none_strings),
        migrations.RunPython(replace_empty_strings),
    ]
