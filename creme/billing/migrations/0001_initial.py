# -*- coding: utf-8 -*-
from decimal import Decimal

from django.conf import settings
from django.db import models, migrations
from django.db.models.deletion import SET_NULL, PROTECT, CASCADE

from creme.creme_core.models import (
    fields as creme_fields,
    CREME_REPLACE_NULL, CREME_REPLACE,
)

from creme.billing.models.fields import BillingDiscountField


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ('contenttypes', '0001_initial'),
        ('creme_core', '0001_initial'),
        migrations.swappable_dependency(settings.PERSONS_ORGANISATION_MODEL),
        migrations.swappable_dependency(settings.PERSONS_ADDRESS_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AdditionalInformation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                ('description', models.TextField(verbose_name='Description', blank=True)),
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
                ('bank_code', models.CharField(max_length=12, verbose_name='Bank code', blank=True)),
                ('counter_code', models.CharField(max_length=12, verbose_name='Counter code', blank=True)),
                ('account_number', models.CharField(max_length=12, verbose_name='Account number', blank=True)),
                ('rib_key', models.CharField(max_length=12, verbose_name='RIB key', blank=True)),
                ('banking_domiciliation', models.CharField(max_length=200, verbose_name='Banking domiciliation', blank=True)),
                ('iban', models.CharField(max_length=100, verbose_name='IBAN', blank=True)),
                ('bic', models.CharField(max_length=100, verbose_name='BIC', blank=True)),
                ('is_default', models.BooleanField(default=False, verbose_name='Is default?')),
                ('organisation', models.ForeignKey(to=settings.PERSONS_ORGANISATION_MODEL, on_delete=CASCADE,
                                                   related_name='PaymentInformationOrganisation_set',
                                                   verbose_name='Target organisation',
                                                  )
                ),
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
                ('description', models.TextField(verbose_name='Description', blank=True)),
                ('is_custom', models.BooleanField(default=True)),
            ],
            options={
                'ordering': ('name',),
                'verbose_name': 'Payment terms',
                'verbose_name_plural': 'Payment terms',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ConfigBillingAlgo',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name_algo', models.CharField(max_length=400, verbose_name='Algo name')),
                ('ct', creme_fields.CTypeForeignKey(to='contenttypes.ContentType')),
                ('organisation', models.ForeignKey(verbose_name='Organisation', to=settings.PERSONS_ORGANISATION_MODEL, on_delete=CASCADE)),
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
                ('order', creme_fields.BasicAutoField(verbose_name='Order', editable=False, blank=True)),
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
                ('cremeentity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False,
                                                         to='creme_core.CremeEntity', on_delete=CASCADE,
                                                        )
                ),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                ('number', models.CharField(max_length=100, verbose_name='Number', blank=True)),
                ('issuing_date', models.DateField(null=True, verbose_name='Issuing date', blank=True)),
                ('expiration_date', models.DateField(null=True, verbose_name='Expiration date', blank=True)),
                ('discount', BillingDiscountField(default=Decimal('0'), verbose_name='Overall discount', max_digits=10, decimal_places=2)),
                ('comment', models.TextField(verbose_name='Comment', blank=True)),
                ('total_vat', creme_fields.MoneyField(decimal_places=2, default=0, editable=False, max_digits=14, blank=True, null=True, verbose_name='Total with VAT')),
                ('total_no_vat', creme_fields.MoneyField(decimal_places=2, default=0, editable=False, max_digits=14, blank=True, null=True, verbose_name='Total without VAT')),
                # ('additional_info', models.ForeignKey(related_name='+', on_delete=SET_NULL, verbose_name='Additional Information', blank=True, to='billing.AdditionalInformation', null=True)),
                ('additional_info', models.ForeignKey(related_name='+', on_delete=CREME_REPLACE_NULL, verbose_name='Additional Information', blank=True, to='billing.AdditionalInformation', null=True)),
                ('currency', models.ForeignKey(related_name='+', on_delete=PROTECT, default=1, verbose_name='Currency', to='creme_core.Currency')),
                ('payment_info', models.ForeignKey(on_delete=SET_NULL, blank=True, editable=False, to='billing.PaymentInformation', null=True, verbose_name='Payment information')),
                # ('payment_terms', models.ForeignKey(related_name='+', on_delete=SET_NULL, verbose_name='Payment Terms', blank=True, to='billing.PaymentTerms', null=True)),
                ('payment_terms', models.ForeignKey(related_name='+', on_delete=CREME_REPLACE_NULL, verbose_name='Payment Terms', blank=True, to='billing.PaymentTerms', null=True)),
                ('billing_address', models.ForeignKey(related_name='+', on_delete=SET_NULL, blank=True, editable=False, to=settings.PERSONS_ADDRESS_MODEL, null=True, verbose_name='Billing address')),
                ('shipping_address', models.ForeignKey(related_name='+', on_delete=SET_NULL, blank=True, editable=False, to=settings.PERSONS_ADDRESS_MODEL, null=True, verbose_name='Shipping address')),

                # ('status', models.ForeignKey(on_delete=PROTECT, verbose_name='Status of credit note', to='billing.CreditNoteStatus')),
                ('status', models.ForeignKey(on_delete=CREME_REPLACE, verbose_name='Status of credit note', to='billing.CreditNoteStatus')),
            ],
            options={
                'swappable': 'BILLING_CREDIT_NOTE_MODEL',
                'ordering': ('name',),
                'verbose_name': 'Credit note',
                'verbose_name_plural': 'Credit notes',
            },
            bases=('creme_core.cremeentity',),
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
                ('order', creme_fields.BasicAutoField(verbose_name='Order', editable=False, blank=True)),
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
                ('cremeentity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False,
                                                         to='creme_core.CremeEntity', on_delete=CASCADE,
                                                        )
                ),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                ('number', models.CharField(max_length=100, verbose_name='Number', blank=True)),
                ('issuing_date', models.DateField(null=True, verbose_name='Issuing date', blank=True)),
                ('expiration_date', models.DateField(null=True, verbose_name='Expiration date', blank=True)),
                ('discount', BillingDiscountField(default=Decimal('0'), verbose_name='Overall discount', max_digits=10, decimal_places=2)),
                ('comment', models.TextField(verbose_name='Comment', blank=True)),
                ('total_vat', creme_fields.MoneyField(decimal_places=2, default=0, editable=False, max_digits=14, blank=True, null=True, verbose_name='Total with VAT')),
                ('total_no_vat', creme_fields.MoneyField(decimal_places=2, default=0, editable=False, max_digits=14, blank=True, null=True, verbose_name='Total without VAT')),
                # ('additional_info', models.ForeignKey(related_name='+', on_delete=SET_NULL, verbose_name='Additional Information', blank=True, to='billing.AdditionalInformation', null=True)),
                ('additional_info', models.ForeignKey(related_name='+', on_delete=CREME_REPLACE_NULL, verbose_name='Additional Information', blank=True, to='billing.AdditionalInformation', null=True)),
                ('currency', models.ForeignKey(related_name='+', on_delete=PROTECT, default=1, verbose_name='Currency', to='creme_core.Currency')),
                ('payment_info', models.ForeignKey(on_delete=SET_NULL, blank=True, editable=False, to='billing.PaymentInformation', null=True, verbose_name='Payment information')),
                # ('payment_terms', models.ForeignKey(related_name='+', on_delete=SET_NULL, verbose_name='Payment Terms', blank=True, to='billing.PaymentTerms', null=True)),
                ('payment_terms', models.ForeignKey(related_name='+', on_delete=CREME_REPLACE_NULL, verbose_name='Payment Terms', blank=True, to='billing.PaymentTerms', null=True)),
                ('billing_address', models.ForeignKey(related_name='+', on_delete=SET_NULL, blank=True, editable=False, to=settings.PERSONS_ADDRESS_MODEL, null=True, verbose_name='Billing address')),
                ('shipping_address', models.ForeignKey(related_name='+', on_delete=SET_NULL, blank=True, editable=False, to=settings.PERSONS_ADDRESS_MODEL, null=True, verbose_name='Shipping address')),

                # ('status', models.ForeignKey(on_delete=PROTECT, verbose_name='Status of invoice', to='billing.InvoiceStatus')),
                ('status', models.ForeignKey(on_delete=CREME_REPLACE, verbose_name='Status of invoice', to='billing.InvoiceStatus')),
                # ('payment_type', models.ForeignKey(on_delete=SET_NULL, verbose_name='Settlement terms', blank=True, to='billing.SettlementTerms', null=True)),
                ('payment_type', models.ForeignKey(on_delete=CREME_REPLACE_NULL, verbose_name='Settlement terms', blank=True, to='billing.SettlementTerms', null=True)),
            ],
            options={
                'swappable': 'BILLING_INVOICE_MODEL',
                'ordering': ('name',),
                'verbose_name': 'Invoice',
                'verbose_name_plural': 'Invoices',
            },
            bases=('creme_core.cremeentity',),
        ),
        migrations.CreateModel(
            name='QuoteStatus',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                ('is_custom', models.BooleanField(default=True)),
                ('order', creme_fields.BasicAutoField(verbose_name='Order', editable=False, blank=True)),
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
                ('cremeentity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False,
                                                         to='creme_core.CremeEntity', on_delete=CASCADE,
                                                        )
                ),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                ('number', models.CharField(max_length=100, verbose_name='Number', blank=True)),
                ('issuing_date', models.DateField(null=True, verbose_name='Issuing date', blank=True)),
                ('expiration_date', models.DateField(null=True, verbose_name='Expiration date', blank=True)),
                ('discount', BillingDiscountField(default=Decimal('0'), verbose_name='Overall discount', max_digits=10, decimal_places=2)),
                ('comment', models.TextField(verbose_name='Comment', blank=True)),
                ('total_vat', creme_fields.MoneyField(decimal_places=2, default=0, editable=False, max_digits=14, blank=True, null=True, verbose_name='Total with VAT')),
                ('total_no_vat', creme_fields.MoneyField(decimal_places=2, default=0, editable=False, max_digits=14, blank=True, null=True, verbose_name='Total without VAT')),
                # ('additional_info', models.ForeignKey(related_name='+', on_delete=SET_NULL, verbose_name='Additional Information', blank=True, to='billing.AdditionalInformation', null=True)),
                ('additional_info', models.ForeignKey(related_name='+', on_delete=CREME_REPLACE_NULL, verbose_name='Additional Information', blank=True, to='billing.AdditionalInformation', null=True)),
                ('currency', models.ForeignKey(related_name='+', on_delete=PROTECT, default=1, verbose_name='Currency', to='creme_core.Currency')),
                ('payment_info', models.ForeignKey(on_delete=SET_NULL, blank=True, editable=False, to='billing.PaymentInformation', null=True, verbose_name='Payment information')),
                # ('payment_terms', models.ForeignKey(related_name='+', on_delete=SET_NULL, verbose_name='Payment Terms', blank=True, to='billing.PaymentTerms', null=True)),
                ('payment_terms', models.ForeignKey(related_name='+', on_delete=CREME_REPLACE_NULL, verbose_name='Payment Terms', blank=True, to='billing.PaymentTerms', null=True)),
                ('billing_address', models.ForeignKey(related_name='+', on_delete=SET_NULL, blank=True, editable=False, to=settings.PERSONS_ADDRESS_MODEL, null=True, verbose_name='Billing address')),
                ('shipping_address', models.ForeignKey(related_name='+', on_delete=SET_NULL, blank=True, editable=False, to=settings.PERSONS_ADDRESS_MODEL, null=True, verbose_name='Shipping address')),

                ('acceptation_date', models.DateField(null=True, verbose_name='Acceptation date', blank=True)),
                # ('status', models.ForeignKey(on_delete=PROTECT, verbose_name='Status of quote', to='billing.QuoteStatus')),
                ('status', models.ForeignKey(on_delete=CREME_REPLACE, verbose_name='Status of quote', to='billing.QuoteStatus')),
            ],
            options={
                'swappable': 'BILLING_QUOTE_MODEL',
                'ordering': ('name',),
                'verbose_name': 'Quote',
                'verbose_name_plural': 'Quotes',
            },
            bases=('creme_core.cremeentity',),
        ),
        migrations.CreateModel(
            name='SalesOrderStatus',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                ('is_custom', models.BooleanField(default=True)),
                ('order', creme_fields.BasicAutoField(verbose_name='Order', editable=False, blank=True)),
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
                ('cremeentity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False,
                                                         to='creme_core.CremeEntity', on_delete=CASCADE,
                                                        )
                ),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                ('number', models.CharField(max_length=100, verbose_name='Number', blank=True)),
                ('issuing_date', models.DateField(null=True, verbose_name='Issuing date', blank=True)),
                ('expiration_date', models.DateField(null=True, verbose_name='Expiration date', blank=True)),
                ('discount', BillingDiscountField(default=Decimal('0'), verbose_name='Overall discount', max_digits=10, decimal_places=2)),
                ('comment', models.TextField(verbose_name='Comment', blank=True)),
                ('total_vat', creme_fields.MoneyField(decimal_places=2, default=0, editable=False, max_digits=14, blank=True, null=True, verbose_name='Total with VAT')),
                ('total_no_vat', creme_fields.MoneyField(decimal_places=2, default=0, editable=False, max_digits=14, blank=True, null=True, verbose_name='Total without VAT')),
                # ('additional_info', models.ForeignKey(related_name='+', on_delete=SET_NULL, verbose_name='Additional Information', blank=True, to='billing.AdditionalInformation', null=True)),
                ('additional_info', models.ForeignKey(related_name='+', on_delete=CREME_REPLACE_NULL, verbose_name='Additional Information', blank=True, to='billing.AdditionalInformation', null=True)),
                ('currency', models.ForeignKey(related_name='+', on_delete=PROTECT, default=1, verbose_name='Currency', to='creme_core.Currency')),
                ('payment_info', models.ForeignKey(on_delete=SET_NULL, blank=True, editable=False, to='billing.PaymentInformation', null=True, verbose_name='Payment information')),
                # ('payment_terms', models.ForeignKey(related_name='+', on_delete=SET_NULL, verbose_name='Payment Terms', blank=True, to='billing.PaymentTerms', null=True)),
                ('payment_terms', models.ForeignKey(related_name='+', on_delete=CREME_REPLACE_NULL, verbose_name='Payment Terms', blank=True, to='billing.PaymentTerms', null=True)),
                ('billing_address', models.ForeignKey(related_name='+', on_delete=SET_NULL, blank=True, editable=False, to=settings.PERSONS_ADDRESS_MODEL, null=True, verbose_name='Billing address')),
                ('shipping_address', models.ForeignKey(related_name='+', on_delete=SET_NULL, blank=True, editable=False, to=settings.PERSONS_ADDRESS_MODEL, null=True, verbose_name='Shipping address')),

                # ('status', models.ForeignKey(on_delete=PROTECT, verbose_name='Status of salesorder', to='billing.SalesOrderStatus')),
                ('status', models.ForeignKey(on_delete=CREME_REPLACE, verbose_name='Status of salesorder', to='billing.SalesOrderStatus')),
            ],
            options={
                'swappable': 'BILLING_SALES_ORDER_MODEL',
                'ordering': ('name',),
                'verbose_name': 'Salesorder',
                'verbose_name_plural': 'Salesorders',
            },
            bases=('creme_core.cremeentity',),
        ),
        migrations.CreateModel(
            name='SimpleBillingAlgo',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('last_number', models.IntegerField()),
                ('prefix', models.CharField(max_length=400, verbose_name='Invoice prefix')),
                ('ct', creme_fields.CTypeForeignKey(to='contenttypes.ContentType')),
                ('organisation', models.ForeignKey(verbose_name='Organisation', to=settings.PERSONS_ORGANISATION_MODEL, on_delete=CASCADE)),
            ],
            options={
                'unique_together': {('organisation', 'last_number', 'ct')},
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TemplateBase',
            fields=[
                ('cremeentity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False,
                                                         to='creme_core.CremeEntity', on_delete=CASCADE,
                                                        )
                ),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                ('number', models.CharField(max_length=100, verbose_name='Number', blank=True)),
                ('issuing_date', models.DateField(null=True, verbose_name='Issuing date', blank=True)),
                ('expiration_date', models.DateField(null=True, verbose_name='Expiration date', blank=True)),
                ('discount', BillingDiscountField(default=Decimal('0'), verbose_name='Overall discount', max_digits=10, decimal_places=2)),
                ('comment', models.TextField(verbose_name='Comment', blank=True)),
                ('total_vat', creme_fields.MoneyField(decimal_places=2, default=0, editable=False, max_digits=14, blank=True, null=True, verbose_name='Total with VAT')),
                ('total_no_vat', creme_fields.MoneyField(decimal_places=2, default=0, editable=False, max_digits=14, blank=True, null=True, verbose_name='Total without VAT')),
                # ('additional_info', models.ForeignKey(related_name='+', on_delete=SET_NULL, verbose_name='Additional Information', blank=True, to='billing.AdditionalInformation', null=True)),
                ('additional_info', models.ForeignKey(related_name='+', on_delete=CREME_REPLACE_NULL, verbose_name='Additional Information', blank=True, to='billing.AdditionalInformation', null=True)),
                ('currency', models.ForeignKey(related_name='+', on_delete=PROTECT, default=1, verbose_name='Currency', to='creme_core.Currency')),
                ('payment_info', models.ForeignKey(on_delete=SET_NULL, blank=True, editable=False, to='billing.PaymentInformation', null=True, verbose_name='Payment information')),
                # ('payment_terms', models.ForeignKey(related_name='+', on_delete=SET_NULL, verbose_name='Payment Terms', blank=True, to='billing.PaymentTerms', null=True)),
                ('payment_terms', models.ForeignKey(related_name='+', on_delete=CREME_REPLACE_NULL, verbose_name='Payment Terms', blank=True, to='billing.PaymentTerms', null=True)),
                ('billing_address', models.ForeignKey(related_name='+', on_delete=SET_NULL, blank=True, editable=False, to=settings.PERSONS_ADDRESS_MODEL, null=True, verbose_name='Billing address')),
                ('shipping_address', models.ForeignKey(related_name='+', on_delete=SET_NULL, blank=True, editable=False, to=settings.PERSONS_ADDRESS_MODEL, null=True, verbose_name='Shipping address')),

                ('status_id', models.PositiveIntegerField(editable=False)),
                ('ct', creme_fields.CTypeForeignKey(editable=False, to='contenttypes.ContentType')),
            ],
            options={
                'swappable': 'BILLING_TEMPLATE_BASE_MODEL',
                'ordering': ('name',),
                'verbose_name': 'Template',
                'verbose_name_plural': 'Templates',
            },
            bases=('creme_core.cremeentity',)
        ),
        migrations.CreateModel(
            name='ProductLine',
            fields=[
                ('cremeentity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False,
                                                         to='creme_core.CremeEntity', on_delete=CASCADE,
                                                        )
                ),
                ('on_the_fly_item', models.CharField(max_length=100, null=True, verbose_name='On-the-fly line')),
                ('comment', models.TextField(verbose_name='Comment', blank=True)),
                ('quantity', models.DecimalField(default=Decimal('1.00'), verbose_name='Quantity', max_digits=10, decimal_places=2)),
                ('unit_price', models.DecimalField(default=Decimal('0'), verbose_name='Unit price', max_digits=10, decimal_places=2)),
                ('unit', models.CharField(max_length=100, verbose_name='Unit', blank=True)),
                ('discount', models.DecimalField(default=Decimal('0'), verbose_name='Discount', max_digits=10, decimal_places=2)),
                ('discount_unit', models.PositiveIntegerField(blank=True, null=True, default=1, editable=False,
                                                              choices=[(1, 'Percent'), (2, 'Amount')],
                                                              verbose_name='Discount Unit',
                                                             )
                ),
                ('total_discount', models.BooleanField(default=False, verbose_name='Total discount ?', editable=False)),
                ('vat_value', models.ForeignKey(on_delete=PROTECT, verbose_name='VAT', blank=True, to='creme_core.Vat', null=True)),
            ],
            options={
                'swappable': 'BILLING_PRODUCT_LINE_MODEL',
                'ordering': ('created',),
                'verbose_name': 'Product line',
                'verbose_name_plural': 'Product lines',
            },
            bases=('creme_core.cremeentity',),
        ),
        migrations.CreateModel(
            name='ServiceLine',
            fields=[
                ('cremeentity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False,
                                                         to='creme_core.CremeEntity', on_delete=CASCADE,
                                                        )
                ),
                ('on_the_fly_item', models.CharField(max_length=100, null=True, verbose_name='On-the-fly line')),
                ('comment', models.TextField(verbose_name='Comment', blank=True)),
                ('quantity', models.DecimalField(default=Decimal('1.00'), verbose_name='Quantity', max_digits=10, decimal_places=2)),
                ('unit_price', models.DecimalField(default=Decimal('0'), verbose_name='Unit price', max_digits=10, decimal_places=2)),
                ('unit', models.CharField(max_length=100, verbose_name='Unit', blank=True)),
                ('discount', models.DecimalField(default=Decimal('0'), verbose_name='Discount', max_digits=10, decimal_places=2)),
                ('discount_unit', models.PositiveIntegerField(blank=True, null=True, default=1, editable=False,
                                                              choices=[(1, 'Percent'), (2, 'Amount')],
                                                              verbose_name='Discount Unit',
                                                             )
                ),
                ('total_discount', models.BooleanField(default=False, verbose_name='Total discount ?', editable=False)),
                ('vat_value', models.ForeignKey(on_delete=PROTECT, verbose_name='VAT', blank=True, to='creme_core.Vat', null=True)),
            ],
            options={
                'swappable': 'BILLING_SERVICE_LINE_MODEL',
                'ordering': ('created',),
                'verbose_name': 'Service line',
                'verbose_name_plural': 'Service lines',
            },
            bases=('creme_core.cremeentity',),
        ),
    ]
