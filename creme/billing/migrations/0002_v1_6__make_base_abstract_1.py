# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from decimal import Decimal

from django.db import models, migrations
import django.db.models.deletion

import creme.creme_core.models.fields


class Migration(migrations.Migration):
    dependencies = [
        ('billing', '0001_initial'),
    ]

    operations = [
        # Step 1: fields of base are added in final classes (Invoice, Quote, SalesOrder, CreditNote, TemplateBase)

        # Step 1.1: FK to CremeEntity
        migrations.AddField(
            model_name='creditnote',
            name='cremeentity_ptr',
            field=models.OneToOneField(
                # NB: temporarily commented
                #parent_link=True, auto_created=True, primary_key=True,
                serialize=False, to='creme_core.CremeEntity',
                null=True, default=None, # temporary values
               ),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='invoice',
            name='cremeentity_ptr',
            field=models.OneToOneField(
                # NB: temporarily commented
                #parent_link=True, auto_created=True, primary_key=True,
                serialize=False, to='creme_core.CremeEntity',
                null=True, default=None, # temporary values
               ),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='quote',
            name='cremeentity_ptr',
            field=models.OneToOneField(
                # NB: temporarily commented
                #parent_link=True, auto_created=True, primary_key=True,
                serialize=False, to='creme_core.CremeEntity',
                null=True, default=None, # temporary values
               ),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='salesorder',
            name='cremeentity_ptr',
            field=models.OneToOneField(
                # NB: temporarily commented
                #parent_link=True, auto_created=True, primary_key=True,
                serialize=False, to='creme_core.CremeEntity',
                null=True, default=None, # temporary values
               ),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='templatebase',
            name='cremeentity_ptr',
            field=models.OneToOneField(
                # NB: temporarily commented
                #parent_link=True, auto_created=True, primary_key=True,
                serialize=False, to='creme_core.CremeEntity',
                null=True, default=None, # temporary values
               ),
            preserve_default=True,
        ),

        # Step 1.2: other fields
        migrations.AddField(
            model_name='creditnote',
            name='additional_info',
            field=models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.SET_NULL, verbose_name='Additional Information', blank=True, to='billing.AdditionalInformation', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='creditnote',
            name='billing_address',
            field=models.ForeignKey(related_name='+', blank=True, editable=False, to='persons.Address', null=True, verbose_name='Billing address'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='creditnote',
            name='comment',
            field=models.TextField(null=True, verbose_name='Comment', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='creditnote',
            name='currency',
            field=models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.PROTECT, default=1, verbose_name='Currency', to='creme_core.Currency'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='creditnote',
            name='discount',
            field=models.DecimalField(default=Decimal('0'), verbose_name='Overall discount', max_digits=10, decimal_places=2),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='creditnote',
            name='expiration_date',
            field=models.DateField(null=True, verbose_name='Expiration date', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='creditnote',
            name='issuing_date',
            field=models.DateField(null=True, verbose_name='Issuing date', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='creditnote',
            name='name',
            field=models.CharField(default=b'Temporary name', max_length=100, verbose_name='Name'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='creditnote',
            name='number',
            field=models.CharField(max_length=100, null=True, verbose_name='Number', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='creditnote',
            name='payment_info',
            field=models.ForeignKey(blank=True, editable=False, to='billing.PaymentInformation', null=True, verbose_name='Payment information'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='creditnote',
            name='payment_terms',
            field=models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.SET_NULL, verbose_name='Payment Terms', blank=True, to='billing.PaymentTerms', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='creditnote',
            name='shipping_address',
            field=models.ForeignKey(related_name='+', blank=True, editable=False, to='persons.Address', null=True, verbose_name='Shipping address'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='creditnote',
            name='total_no_vat',
            field=creme.creme_core.models.fields.MoneyField(decimal_places=2, default=0, editable=False, max_digits=14, blank=True, null=True, verbose_name='Total without VAT'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='creditnote',
            name='total_vat',
            field=creme.creme_core.models.fields.MoneyField(decimal_places=2, default=0, editable=False, max_digits=14, blank=True, null=True, verbose_name='Total with VAT'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='invoice',
            name='additional_info',
            field=models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.SET_NULL, verbose_name='Additional Information', blank=True, to='billing.AdditionalInformation', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='invoice',
            name='billing_address',
            field=models.ForeignKey(related_name='+', blank=True, editable=False, to='persons.Address', null=True, verbose_name='Billing address'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='invoice',
            name='comment',
            field=models.TextField(null=True, verbose_name='Comment', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='invoice',
            name='currency',
            field=models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.PROTECT, default=1, verbose_name='Currency', to='creme_core.Currency'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='invoice',
            name='discount',
            field=models.DecimalField(default=Decimal('0'), verbose_name='Overall discount', max_digits=10, decimal_places=2),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='invoice',
            name='expiration_date',
            field=models.DateField(null=True, verbose_name='Expiration date', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='invoice',
            name='issuing_date',
            field=models.DateField(null=True, verbose_name='Issuing date', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='invoice',
            name='name',
            field=models.CharField(default=b'Temporary name', max_length=100, verbose_name='Name'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='invoice',
            name='number',
            field=models.CharField(max_length=100, null=True, verbose_name='Number', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='invoice',
            name='payment_info',
            field=models.ForeignKey(blank=True, editable=False, to='billing.PaymentInformation', null=True, verbose_name='Payment information'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='invoice',
            name='payment_terms',
            field=models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.SET_NULL, verbose_name='Payment Terms', blank=True, to='billing.PaymentTerms', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='invoice',
            name='shipping_address',
            field=models.ForeignKey(related_name='+', blank=True, editable=False, to='persons.Address', null=True, verbose_name='Shipping address'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='invoice',
            name='total_no_vat',
            field=creme.creme_core.models.fields.MoneyField(decimal_places=2, default=0, editable=False, max_digits=14, blank=True, null=True, verbose_name='Total without VAT'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='invoice',
            name='total_vat',
            field=creme.creme_core.models.fields.MoneyField(decimal_places=2, default=0, editable=False, max_digits=14, blank=True, null=True, verbose_name='Total with VAT'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='quote',
            name='additional_info',
            field=models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.SET_NULL, verbose_name='Additional Information', blank=True, to='billing.AdditionalInformation', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='quote',
            name='billing_address',
            field=models.ForeignKey(related_name='+', blank=True, editable=False, to='persons.Address', null=True, verbose_name='Billing address'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='quote',
            name='comment',
            field=models.TextField(null=True, verbose_name='Comment', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='quote',
            name='currency',
            field=models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.PROTECT, default=1, verbose_name='Currency', to='creme_core.Currency'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='quote',
            name='discount',
            field=models.DecimalField(default=Decimal('0'), verbose_name='Overall discount', max_digits=10, decimal_places=2),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='quote',
            name='expiration_date',
            field=models.DateField(null=True, verbose_name='Expiration date', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='quote',
            name='issuing_date',
            field=models.DateField(null=True, verbose_name='Issuing date', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='quote',
            name='name',
            field=models.CharField(default=b'Temporary name', max_length=100, verbose_name='Name'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='quote',
            name='number',
            field=models.CharField(max_length=100, null=True, verbose_name='Number', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='quote',
            name='payment_info',
            field=models.ForeignKey(blank=True, editable=False, to='billing.PaymentInformation', null=True, verbose_name='Payment information'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='quote',
            name='payment_terms',
            field=models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.SET_NULL, verbose_name='Payment Terms', blank=True, to='billing.PaymentTerms', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='quote',
            name='shipping_address',
            field=models.ForeignKey(related_name='+', blank=True, editable=False, to='persons.Address', null=True, verbose_name='Shipping address'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='quote',
            name='total_no_vat',
            field=creme.creme_core.models.fields.MoneyField(decimal_places=2, default=0, editable=False, max_digits=14, blank=True, null=True, verbose_name='Total without VAT'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='quote',
            name='total_vat',
            field=creme.creme_core.models.fields.MoneyField(decimal_places=2, default=0, editable=False, max_digits=14, blank=True, null=True, verbose_name='Total with VAT'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='salesorder',
            name='additional_info',
            field=models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.SET_NULL, verbose_name='Additional Information', blank=True, to='billing.AdditionalInformation', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='salesorder',
            name='billing_address',
            field=models.ForeignKey(related_name='+', blank=True, editable=False, to='persons.Address', null=True, verbose_name='Billing address'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='salesorder',
            name='comment',
            field=models.TextField(null=True, verbose_name='Comment', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='salesorder',
            name='currency',
            field=models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.PROTECT, default=1, verbose_name='Currency', to='creme_core.Currency'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='salesorder',
            name='discount',
            field=models.DecimalField(default=Decimal('0'), verbose_name='Overall discount', max_digits=10, decimal_places=2),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='salesorder',
            name='expiration_date',
            field=models.DateField(null=True, verbose_name='Expiration date', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='salesorder',
            name='issuing_date',
            field=models.DateField(null=True, verbose_name='Issuing date', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='salesorder',
            name='name',
            field=models.CharField(default=b'Temporary name', max_length=100, verbose_name='Name'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='salesorder',
            name='number',
            field=models.CharField(max_length=100, null=True, verbose_name='Number', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='salesorder',
            name='payment_info',
            field=models.ForeignKey(blank=True, editable=False, to='billing.PaymentInformation', null=True, verbose_name='Payment information'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='salesorder',
            name='payment_terms',
            field=models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.SET_NULL, verbose_name='Payment Terms', blank=True, to='billing.PaymentTerms', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='salesorder',
            name='shipping_address',
            field=models.ForeignKey(related_name='+', blank=True, editable=False, to='persons.Address', null=True, verbose_name='Shipping address'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='salesorder',
            name='total_no_vat',
            field=creme.creme_core.models.fields.MoneyField(decimal_places=2, default=0, editable=False, max_digits=14, blank=True, null=True, verbose_name='Total without VAT'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='salesorder',
            name='total_vat',
            field=creme.creme_core.models.fields.MoneyField(decimal_places=2, default=0, editable=False, max_digits=14, blank=True, null=True, verbose_name='Total with VAT'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='templatebase',
            name='additional_info',
            field=models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.SET_NULL, verbose_name='Additional Information', blank=True, to='billing.AdditionalInformation', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='templatebase',
            name='billing_address',
            field=models.ForeignKey(related_name='+', blank=True, editable=False, to='persons.Address', null=True, verbose_name='Billing address'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='templatebase',
            name='comment',
            field=models.TextField(null=True, verbose_name='Comment', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='templatebase',
            name='currency',
            field=models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.PROTECT, default=1, verbose_name='Currency', to='creme_core.Currency'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='templatebase',
            name='discount',
            field=models.DecimalField(default=Decimal('0'), verbose_name='Overall discount', max_digits=10, decimal_places=2),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='templatebase',
            name='expiration_date',
            field=models.DateField(null=True, verbose_name='Expiration date', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='templatebase',
            name='issuing_date',
            field=models.DateField(null=True, verbose_name='Issuing date', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='templatebase',
            name='name',
            field=models.CharField(default=b'Temporary name', max_length=100, verbose_name='Name'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='templatebase',
            name='number',
            field=models.CharField(max_length=100, null=True, verbose_name='Number', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='templatebase',
            name='payment_info',
            field=models.ForeignKey(blank=True, editable=False, to='billing.PaymentInformation', null=True, verbose_name='Payment information'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='templatebase',
            name='payment_terms',
            field=models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.SET_NULL, verbose_name='Payment Terms', blank=True, to='billing.PaymentTerms', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='templatebase',
            name='shipping_address',
            field=models.ForeignKey(related_name='+', blank=True, editable=False, to='persons.Address', null=True, verbose_name='Shipping address'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='templatebase',
            name='total_no_vat',
            field=creme.creme_core.models.fields.MoneyField(decimal_places=2, default=0, editable=False, max_digits=14, blank=True, null=True, verbose_name='Total without VAT'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='templatebase',
            name='total_vat',
            field=creme.creme_core.models.fields.MoneyField(decimal_places=2, default=0, editable=False, max_digits=14, blank=True, null=True, verbose_name='Total with VAT'),
            preserve_default=True,
        ),
    ]
