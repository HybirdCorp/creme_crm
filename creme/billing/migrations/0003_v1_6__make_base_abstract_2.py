# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
#from django.db.models import F

from creme.billing import (credit_note_model_is_custom, invoice_model_is_custom,
    quote_model_is_custom, sales_order_model_is_custom, template_base_model_is_custom)


def copy_old_fields(apps, schema_editor):
    field_names = (
            'cremeentity_ptr',
            'name',
            'number',
            'issuing_date',
            'expiration_date',
            'discount',
            'billing_address_id',
            'shipping_address_id',
            'currency_id',
            'comment',
            'total_vat',
            'total_no_vat',
            'additional_info_id',
            'payment_terms_id',
            'payment_info_id',
        )

    for model_name, custom_func in [('Invoice',      invoice_model_is_custom),
                                    ('Quote',        quote_model_is_custom),
                                    ('SalesOrder',   sales_order_model_is_custom),
                                    ('CreditNote',   credit_note_model_is_custom),
                                    ('TemplateBase', template_base_model_is_custom),
                                   ]:
        if custom_func():
            continue

        # NB: It cannot be done with F expressions because it does not work with field from JOIN
        for instance in apps.get_model('billing', model_name).objects.all():
            base_instance = instance.base_ptr

            for field_name in field_names:
                #setattr(instance, field_name, getattr(instance, 'base_ptr.' + field_name))
                setattr(instance, field_name, getattr(base_instance, field_name))
                instance.save()


class Migration(migrations.Migration):
    dependencies = [
        ('billing', '0002_v1_6__make_base_abstract_1'),
    ]

    operations = [
        # Step 2: values of Base fields are copied.
        migrations.RunPython(copy_old_fields),
    ]
