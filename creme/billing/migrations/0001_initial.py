# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from decimal import Decimal

from django.conf import settings
from django.db import models, migrations
import django.db.models.deletion

import creme.creme_core.models.fields


class Migration(migrations.Migration):
    dependencies = [
        ('contenttypes', '0001_initial'),
        ('creme_core', '0001_initial'),
        #('persons', '0001_initial'),
        migrations.swappable_dependency(settings.PERSONS_ORGANISATION_MODEL),
        migrations.swappable_dependency(settings.PERSONS_ADDRESS_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AdditionalInformation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                ('description', models.TextField(null=True, verbose_name='Description', blank=True)),
                ('is_custom', models.BooleanField(default=True)),
            ],
            options={
                'ordering': ('name',),
                'verbose_name': 'Additional information',
                'verbose_name_plural': 'Additional information',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='PaymentInformation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=200, verbose_name='Name')),
                ('bank_code', models.CharField(max_length=12, null=True, verbose_name='Bank code', blank=True)),
                ('counter_code', models.CharField(max_length=12, null=True, verbose_name='Counter code', blank=True)),
                ('account_number', models.CharField(max_length=12, null=True, verbose_name='Account number', blank=True)),
                ('rib_key', models.CharField(max_length=12, null=True, verbose_name='RIB key', blank=True)),
                ('banking_domiciliation', models.CharField(max_length=200, null=True, verbose_name='Banking domiciliation', blank=True)),
                ('iban', models.CharField(max_length=100, null=True, verbose_name='IBAN', blank=True)),
                ('bic', models.CharField(max_length=100, null=True, verbose_name='BIC', blank=True)),
                ('is_default', models.BooleanField(default=False, verbose_name='Is default?')),
                #('organisation', models.ForeignKey(related_name='PaymentInformationOrganisation_set', verbose_name='Target organisation', to='persons.Organisation')),
                ('organisation', models.ForeignKey(related_name='PaymentInformationOrganisation_set', verbose_name='Target organisation', to=settings.PERSONS_ORGANISATION_MODEL)),
            ],
            options={
                'ordering': ('name',),
                'verbose_name': 'Payment information',
                'verbose_name_plural': 'Payment information',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='PaymentTerms',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100, verbose_name='Payment terms')),
                ('description', models.TextField(null=True, verbose_name='Description', blank=True)),
                ('is_custom', models.BooleanField(default=True)),
            ],
            options={
                'ordering': ('name',),
                'verbose_name': 'Payment terms',
                'verbose_name_plural': 'Payments terms',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Base',
            fields=[
                ('cremeentity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='creme_core.CremeEntity')),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                ('number', models.CharField(max_length=100, null=True, verbose_name='Number', blank=True)),
                ('issuing_date', models.DateField(null=True, verbose_name='Issuing date', blank=True)),
                ('expiration_date', models.DateField(null=True, verbose_name='Expiration date', blank=True)),
                ('discount', models.DecimalField(default=Decimal('0'), verbose_name='Overall discount', max_digits=10, decimal_places=2)),
                ('comment', models.TextField(null=True, verbose_name='Comment', blank=True)),
                ('total_vat', creme.creme_core.models.fields.MoneyField(decimal_places=2, default=0, editable=False, max_digits=14, blank=True, null=True, verbose_name='Total with VAT')),
                ('total_no_vat', creme.creme_core.models.fields.MoneyField(decimal_places=2, default=0, editable=False, max_digits=14, blank=True, null=True, verbose_name='Total without VAT')),
                ('additional_info', models.ForeignKey(related_name='AdditionalInformation_set', on_delete=django.db.models.deletion.SET_NULL, verbose_name='Additional Information', blank=True, to='billing.AdditionalInformation', null=True)),
                ('currency', models.ForeignKey(related_name='Currency_set', on_delete=django.db.models.deletion.PROTECT, default=1, verbose_name='Currency', to='creme_core.Currency')),
                ('payment_info', models.ForeignKey(blank=True, editable=False, to='billing.PaymentInformation', null=True, verbose_name='Payment information')),
                ('payment_terms', models.ForeignKey(related_name='PaymentTerms_set', on_delete=django.db.models.deletion.SET_NULL, verbose_name='Payment Terms', blank=True, to='billing.PaymentTerms', null=True)),
                #('billing_address', models.ForeignKey(related_name='BillingAddress_set', blank=True, editable=False, to='persons.Address', null=True, verbose_name='Billing address')),
                ('billing_address', models.ForeignKey(related_name='BillingAddress_set', blank=True, editable=False, to=settings.PERSONS_ADDRESS_MODEL, null=True, verbose_name='Billing address')),
                #('shipping_address', models.ForeignKey(related_name='ShippingAddress_set', blank=True, editable=False, to='persons.Address', null=True, verbose_name='Shipping address')),
                ('shipping_address', models.ForeignKey(related_name='ShippingAddress_set', blank=True, editable=False, to=settings.PERSONS_ADDRESS_MODEL, null=True, verbose_name='Shipping address')),
            ],
            options={
                'ordering': ('name',),
            },
            bases=('creme_core.cremeentity',),
        ),
        migrations.CreateModel(
            name='ConfigBillingAlgo',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name_algo', models.CharField(max_length=400, verbose_name='Algo name')),
                ('ct', creme.creme_core.models.fields.CTypeForeignKey(to='contenttypes.ContentType')),
#                ('organisation', models.ForeignKey(verbose_name='Organisation', to='persons.Organisation')),
                ('organisation', models.ForeignKey(verbose_name='Organisation', to=settings.PERSONS_ORGANISATION_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='CreditNoteStatus',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                ('is_custom', models.BooleanField(default=True)),
                ('order', creme.creme_core.models.fields.BasicAutoField(verbose_name='Order', editable=False, blank=True)),
            ],
            options={
                'ordering': ('order',),
                'abstract': False,
                'verbose_name': 'Credit note status',
                'verbose_name_plural': 'Credit note statuses',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='CreditNote',
            fields=[
                #('base_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='billing.Base')),
                ('base_ptr', models.OneToOneField(parent_link=False, auto_created=True, primary_key=True, serialize=False, to='billing.Base')),
                ('status', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, verbose_name='Status of credit note', to='billing.CreditNoteStatus')),
            ],
            options={
                'swappable': 'BILLING_CREDIT_NOTE_MODEL',
                'verbose_name': 'Credit note',
                'verbose_name_plural': 'Credit notes',
            },
            #bases=('billing.base',),
            bases=(models.Model,), #TODO: ('creme_core.cremeentity',) in creme1.7
        ),
        migrations.CreateModel(
            name='SettlementTerms',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100, verbose_name='Settlement terms')),
            ],
            options={
                'ordering': ('name',),
                'verbose_name': 'Settlement terms',
                'verbose_name_plural': 'Settlement terms',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='InvoiceStatus',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                ('is_custom', models.BooleanField(default=True)),
                ('order', creme.creme_core.models.fields.BasicAutoField(verbose_name='Order', editable=False, blank=True)),
                ('pending_payment', models.BooleanField(default=False, verbose_name='Pending payment')),
            ],
            options={
                'ordering': ('order',),
                'abstract': False,
                'verbose_name': 'Invoice status',
                'verbose_name_plural': 'Invoice statuses',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Invoice',
            fields=[
                #('base_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='billing.Base')),
                ('base_ptr', models.OneToOneField(parent_link=False, auto_created=True, primary_key=True, serialize=False, to='billing.Base')),
                ('status', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, verbose_name='Status of invoice', to='billing.InvoiceStatus')),
                ('payment_type', models.ForeignKey(verbose_name='Settlement terms', blank=True, to='billing.SettlementTerms', null=True)),
            ],
            options={
                'swappable': 'BILLING_INVOICE_MODEL',
                'verbose_name': 'Invoice',
                'verbose_name_plural': 'Invoices',
            },
            #bases=('billing.base',),
            bases=(models.Model,), #TODO: ('creme_core.cremeentity',) in creme1.7
        ),
        migrations.CreateModel(
            name='Line',
            fields=[
                ('cremeentity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='creme_core.CremeEntity')),
                ('on_the_fly_item', models.CharField(max_length=100, null=True, verbose_name='On-the-fly line', blank=True)),
                ('comment', models.TextField(null=True, verbose_name='Comment', blank=True)),
                ('quantity', models.DecimalField(default=Decimal('1.00'), verbose_name='Quantity', max_digits=10, decimal_places=2)),
                ('unit_price', models.DecimalField(default=Decimal('0'), verbose_name='Unit price', max_digits=10, decimal_places=2)),
                ('unit', models.CharField(max_length=100, null=True, verbose_name='Unit', blank=True)),
                ('discount', models.DecimalField(default=Decimal('0'), verbose_name='Discount', max_digits=10, decimal_places=2)),
                ('discount_unit', models.PositiveIntegerField(default=1, editable=False, choices=[(1, 'Percent'), (2, 'Amount')], blank=True, null=True, verbose_name='Discount Unit')),
                ('total_discount', models.BooleanField(default=False, verbose_name='Total discount ?', editable=False)),
                ('type', models.IntegerField(verbose_name='Type', editable=False, choices=[(1, 'Product'), (2, 'Service')])),
                ('vat_value', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, verbose_name='VAT', blank=True, to='creme_core.Vat', null=True)),
            ],
            options={
                'ordering': ('created',),
                'verbose_name': 'Line',
                'verbose_name_plural': 'Lines',
            },
            bases=('creme_core.cremeentity',),
        ),
        migrations.CreateModel(
            name='ProductLine',
            fields=[
                ('line_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='billing.Line')),
            ],
            options={
                'swappable': 'BILLING_PRODUCT_LINE_MODEL',
                'verbose_name': 'Product line',
                'verbose_name_plural': 'Product lines',
            },
            #bases=('billing.line',),
            bases=(models.Model,), #TODO: ('creme_core.cremeentity',) in creme1.7
        ),
        migrations.CreateModel(
            name='QuoteStatus',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                ('is_custom', models.BooleanField(default=True)),
                ('order', creme.creme_core.models.fields.BasicAutoField(verbose_name='Order', editable=False, blank=True)),
                ('won', models.BooleanField(default=False, verbose_name='Won')),
            ],
            options={
                'ordering': ('order',),
                'abstract': False,
                'verbose_name': 'Quote status',
                'verbose_name_plural': 'Quote statuses',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Quote',
            fields=[
                #('base_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='billing.Base')),
                ('base_ptr', models.OneToOneField(parent_link=False, auto_created=True, primary_key=True, serialize=False, to='billing.Base')),
                ('acceptation_date', models.DateField(null=True, verbose_name='Acceptation date', blank=True)),
                ('status', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, verbose_name='Status of quote', to='billing.QuoteStatus')),
            ],
            options={
                'swappable': 'BILLING_QUOTE_MODEL',
                'verbose_name': 'Quote',
                'verbose_name_plural': 'Quotes',
            },
            #bases=('billing.base',),
            bases=(models.Model,), #TODO: ('creme_core.cremeentity',) in creme1.7
        ),
        migrations.CreateModel(
            name='SalesOrderStatus',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                ('is_custom', models.BooleanField(default=True)),
                ('order', creme.creme_core.models.fields.BasicAutoField(verbose_name='Order', editable=False, blank=True)),
            ],
            options={
                'ordering': ('order',),
                'abstract': False,
                'verbose_name': 'Sales order status',
                'verbose_name_plural': 'Sales order statuses',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SalesOrder',
            fields=[
                #('base_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='billing.Base')),
                ('base_ptr', models.OneToOneField(parent_link=False, auto_created=True, primary_key=True, serialize=False, to='billing.Base')),
                ('status', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, verbose_name='Status of salesorder', to='billing.SalesOrderStatus')),
            ],
            options={
                'swappable': 'BILLING_SALES_ORDER_MODEL',
                'verbose_name': 'Salesorder',
                'verbose_name_plural': 'Salesorders',
            },
            #bases=('billing.base',),
            bases=(models.Model,), #TODO: ('creme_core.cremeentity',) in creme1.7
        ),
        migrations.CreateModel(
            name='ServiceLine',
            fields=[
                ('line_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='billing.Line')),
            ],
            options={
                'swappable': 'BILLING_SERVICE_LINE_MODEL',
                'verbose_name': 'Service line',
                'verbose_name_plural': 'Service lines',
            },
            #bases=('billing.line',),
            bases=(models.Model,), #TODO: ('creme_core.cremeentity',) in creme1.7
        ),
        migrations.CreateModel(
            name='SimpleBillingAlgo',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('last_number', models.IntegerField()),
                ('prefix', models.CharField(max_length=400, verbose_name='Invoice prefix')),
                ('ct', creme.creme_core.models.fields.CTypeForeignKey(to='contenttypes.ContentType')),
                #('organisation', models.ForeignKey(verbose_name='Organisation', to='persons.Organisation')),
                ('organisation', models.ForeignKey(verbose_name='Organisation', to=settings.PERSONS_ORGANISATION_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TemplateBase',
            fields=[
                #('base_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='billing.Base')),
                ('base_ptr', models.OneToOneField(parent_link=False, auto_created=True, primary_key=True, serialize=False, to='billing.Base')),
                ('status_id', models.PositiveIntegerField(editable=False)),
                ('ct', creme.creme_core.models.fields.CTypeForeignKey(editable=False, to='contenttypes.ContentType')),
            ],
            options={
                'swappable': 'BILLING_TEMPLATE_BASE_MODEL',
                'verbose_name': 'Template',
                'verbose_name_plural': 'Templates',
            },
            #bases=('billing.base',),
            bases=(models.Model,), #TODO: ('creme_core.cremeentity',) in creme1.7
        ),
        migrations.AlterUniqueTogether(
            name='simplebillingalgo',
            unique_together=set([('organisation', 'last_number', 'ct')]),
        ),
    ]
