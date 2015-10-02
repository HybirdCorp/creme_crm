# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import models, migrations
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('billing', '0007_v1_6__make_line_abstract_3'),
    ]

    operations = [
        migrations.AlterField(
            model_name='creditnote',
            name='billing_address',
            field=models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.SET_NULL, blank=True, editable=False, to=settings.PERSONS_ADDRESS_MODEL, null=True, verbose_name='Billing address'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='creditnote',
            name='payment_info',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, editable=False, to='billing.PaymentInformation', null=True, verbose_name='Payment information'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='creditnote',
            name='shipping_address',
            field=models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.SET_NULL, blank=True, editable=False, to=settings.PERSONS_ADDRESS_MODEL, null=True, verbose_name='Shipping address'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='invoice',
            name='billing_address',
            field=models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.SET_NULL, blank=True, editable=False, to=settings.PERSONS_ADDRESS_MODEL, null=True, verbose_name='Billing address'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='invoice',
            name='payment_info',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, editable=False, to='billing.PaymentInformation', null=True, verbose_name='Payment information'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='invoice',
            name='payment_type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, verbose_name='Settlement terms', blank=True, to='billing.SettlementTerms', null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='invoice',
            name='shipping_address',
            field=models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.SET_NULL, blank=True, editable=False, to=settings.PERSONS_ADDRESS_MODEL, null=True, verbose_name='Shipping address'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='quote',
            name='billing_address',
            field=models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.SET_NULL, blank=True, editable=False, to=settings.PERSONS_ADDRESS_MODEL, null=True, verbose_name='Billing address'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='quote',
            name='payment_info',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, editable=False, to='billing.PaymentInformation', null=True, verbose_name='Payment information'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='quote',
            name='shipping_address',
            field=models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.SET_NULL, blank=True, editable=False, to=settings.PERSONS_ADDRESS_MODEL, null=True, verbose_name='Shipping address'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='salesorder',
            name='billing_address',
            field=models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.SET_NULL, blank=True, editable=False, to=settings.PERSONS_ADDRESS_MODEL, null=True, verbose_name='Billing address'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='salesorder',
            name='payment_info',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, editable=False, to='billing.PaymentInformation', null=True, verbose_name='Payment information'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='salesorder',
            name='shipping_address',
            field=models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.SET_NULL, blank=True, editable=False, to=settings.PERSONS_ADDRESS_MODEL, null=True, verbose_name='Shipping address'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='templatebase',
            name='billing_address',
            field=models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.SET_NULL, blank=True, editable=False, to=settings.PERSONS_ADDRESS_MODEL, null=True, verbose_name='Billing address'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='templatebase',
            name='payment_info',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, editable=False, to='billing.PaymentInformation', null=True, verbose_name='Payment information'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='templatebase',
            name='shipping_address',
            field=models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.SET_NULL, blank=True, editable=False, to=settings.PERSONS_ADDRESS_MODEL, null=True, verbose_name='Shipping address'),
            preserve_default=True,
        ),
    ]
