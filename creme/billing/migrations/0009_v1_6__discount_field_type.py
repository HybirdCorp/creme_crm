# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from decimal import Decimal

from django.db import migrations

import creme.billing.models.fields


class Migration(migrations.Migration):
    dependencies = [
        ('billing', '0008_v1_6__fk_on_delete_set'),
    ]

    operations = [
        migrations.AlterField(
            model_name='creditnote',
            name='discount',
            field=creme.billing.models.fields.BillingDiscountField(default=Decimal('0'), verbose_name='Overall discount', max_digits=10, decimal_places=2),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='discount',
            field=creme.billing.models.fields.BillingDiscountField(default=Decimal('0'), verbose_name='Overall discount', max_digits=10, decimal_places=2),
        ),
        migrations.AlterField(
            model_name='quote',
            name='discount',
            field=creme.billing.models.fields.BillingDiscountField(default=Decimal('0'), verbose_name='Overall discount', max_digits=10, decimal_places=2),
        ),
        migrations.AlterField(
            model_name='salesorder',
            name='discount',
            field=creme.billing.models.fields.BillingDiscountField(default=Decimal('0'), verbose_name='Overall discount', max_digits=10, decimal_places=2),
        ),
        migrations.AlterField(
            model_name='templatebase',
            name='discount',
            field=creme.billing.models.fields.BillingDiscountField(default=Decimal('0'), verbose_name='Overall discount', max_digits=10, decimal_places=2),
        ),
    ]
