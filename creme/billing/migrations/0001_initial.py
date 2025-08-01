from decimal import Decimal
from uuid import uuid4

from django.conf import settings
from django.db import migrations, models
from django.db.models.deletion import CASCADE, PROTECT, SET_NULL

import creme.creme_core.models.fields as core_fields
from creme.billing.models import other_models
from creme.billing.models.fields import BillingDiscountField
from creme.creme_core.models import CREME_REPLACE, CREME_REPLACE_NULL
from creme.creme_core.models.currency import get_default_currency_pk
from creme.creme_core.models.vat import get_default_vat_pk


class Migration(migrations.Migration):
    # replaces = [
    #     ('billing', '0001_initial'),
    #     ('billing', '0032_v2_6__statuses_is_default01,),
    #     ('billing', '0033_v2_6__statuses_is_default02,),
    #     ('billing', '0034_v2_6__fix_uuids,),
    #     ('billing', '0035_v2_6__settingvalue_json,),
    # ]

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
                ('uuid', models.UUIDField(default=uuid4, editable=False, unique=True)),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                ('description', models.TextField(verbose_name='Description', blank=True)),
                ('is_custom', models.BooleanField(default=True, editable=False)),
                ('extra_data', models.JSONField(default=dict, editable=False)),
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
                (
                    'organisation',
                    models.ForeignKey(
                        to=settings.PERSONS_ORGANISATION_MODEL, on_delete=CASCADE,
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
                ('uuid', models.UUIDField(default=uuid4, editable=False, unique=True)),
                ('name', models.CharField(max_length=100, verbose_name='Payment terms')),
                ('description', models.TextField(verbose_name='Description', blank=True)),
                ('is_custom', models.BooleanField(default=True, editable=False)),
                ('extra_data', models.JSONField(default=dict, editable=False)),
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
                ('ct', core_fields.CTypeForeignKey(to='contenttypes.ContentType')),
                (
                    'organisation',
                    models.ForeignKey(verbose_name='Organisation', to=settings.PERSONS_ORGANISATION_MODEL, on_delete=CASCADE)
                ),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SettlementTerms',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', models.UUIDField(default=uuid4, editable=False, unique=True)),
                ('name', models.CharField(max_length=100, verbose_name='Settlement terms')),
                ('extra_data', models.JSONField(default=dict, editable=False)),
                ('is_custom', models.BooleanField(default=True, editable=False)),
            ],
            options={
                'ordering': ('name',),
                'verbose_name': 'Settlement terms',
                'verbose_name_plural': 'Settlement terms',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='CreditNoteStatus',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', models.UUIDField(default=uuid4, editable=False, unique=True)),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                (
                    'color',
                    core_fields.ColorField(
                        default=core_fields.ColorField.random,
                        max_length=6, verbose_name='Color',
                    )
                ),
                ('is_default', models.BooleanField(default=False, verbose_name='Is default?')),
                ('is_custom', models.BooleanField(default=True, editable=False)),
                ('order', core_fields.BasicAutoField(editable=False, blank=True)),
                ('extra_data', models.JSONField(default=dict, editable=False)),
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
                (
                    'cremeentity_ptr',
                    models.OneToOneField(
                        parent_link=True, auto_created=True, primary_key=True, serialize=False,
                        to='creme_core.CremeEntity', on_delete=CASCADE,
                    )
                ),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                ('number', models.CharField(max_length=100, verbose_name='Number', blank=True)),
                ('issuing_date', models.DateField(null=True, verbose_name='Issuing date', blank=True)),
                ('expiration_date', models.DateField(null=True, verbose_name='Expiration date', blank=True)),
                (
                    'discount',
                    BillingDiscountField(
                        default=Decimal('0'), verbose_name='Overall discount', max_digits=10, decimal_places=2,
                    )
                ),
                ('comment', models.TextField(verbose_name='Comment', blank=True)),
                (
                    'total_vat',
                    core_fields.MoneyField(
                        verbose_name='Total with VAT',
                        decimal_places=2, default=0, max_digits=14, null=True,
                        blank=True, editable=False,
                    )
                ),
                (
                    'total_no_vat',
                    core_fields.MoneyField(
                        verbose_name='Total without VAT',
                        decimal_places=2, default=0, max_digits=14,null=True,
                        blank=True, editable=False,
                    )
                ),
                (
                    'additional_info',
                    models.ForeignKey(
                        verbose_name='Additional Information', to='billing.AdditionalInformation',
                        related_name='+', on_delete=CREME_REPLACE_NULL, blank=True, null=True,
                    )
                ),
                (
                    'currency',
                    models.ForeignKey(
                        verbose_name='Currency', to='creme_core.Currency',
                        related_name='+', on_delete=PROTECT,
                        # default=1,
                        default=get_default_currency_pk,
                    )
                ),
                (
                    'payment_terms',
                    models.ForeignKey(
                        verbose_name='Payment Terms', to='billing.PaymentTerms',
                        related_name='+', on_delete=CREME_REPLACE_NULL, blank=True, null=True,
                    )
                ),
                (
                    'payment_info',
                    models.ForeignKey(
                        verbose_name='Payment information', to='billing.PaymentInformation',
                        on_delete=SET_NULL, blank=True, editable=False, null=True,
                    )
                ),
                (
                    'payment_type',
                    models.ForeignKey(
                        verbose_name='Settlement terms', to='billing.settlementterms',
                        blank=True, null=True, on_delete=CREME_REPLACE_NULL,
                    )
                ),
                (
                    'billing_address',
                    models.ForeignKey(
                        verbose_name='Billing address',
                        to=settings.PERSONS_ADDRESS_MODEL,
                        related_name='+', on_delete=SET_NULL, editable=False, null=True,
                    )
                ),
                (
                    'shipping_address',
                    models.ForeignKey(
                        verbose_name='Shipping address',
                        to=settings.PERSONS_ADDRESS_MODEL,
                        related_name='+', on_delete=SET_NULL, editable=False, null=True,
                    )
                ),

                (
                    'status',
                    models.ForeignKey(
                        verbose_name='Status of credit note',
                        to='billing.CreditNoteStatus', on_delete=CREME_REPLACE,
                        default=other_models.get_default_credit_note_status_pk,
                    )
                ),
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
            name='InvoiceStatus',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', models.UUIDField(default=uuid4, editable=False, unique=True)),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                (
                    'color',
                    core_fields.ColorField(
                        default=core_fields.ColorField.random,
                        max_length=6, verbose_name='Color',
                    )
                ),
                ('is_default', models.BooleanField(default=False, verbose_name='Is default?')),
                ('is_custom', models.BooleanField(default=True, editable=False)),
                ('order', core_fields.BasicAutoField(editable=False, blank=True)),
                ('pending_payment', models.BooleanField(default=False, verbose_name='Pending payment')),
                (
                    'is_validated',
                    models.BooleanField(
                        default=False, verbose_name='Is validated?',
                        help_text='If true, the status is used when an Invoice number is generated.',
                    )
                ),
                ('extra_data', models.JSONField(default=dict, editable=False)),
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
                (
                    'cremeentity_ptr',
                    models.OneToOneField(
                        parent_link=True, auto_created=True, primary_key=True, serialize=False,
                        to='creme_core.CremeEntity', on_delete=CASCADE,
                    )
                ),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                ('number', models.CharField(max_length=100, verbose_name='Number', blank=True)),
                ('issuing_date', models.DateField(null=True, verbose_name='Issuing date', blank=True)),
                ('expiration_date', models.DateField(null=True, verbose_name='Expiration date', blank=True)),
                (
                    'discount',
                    BillingDiscountField(
                        default=Decimal('0'), verbose_name='Overall discount', max_digits=10, decimal_places=2,
                    )
                ),
                ('comment', models.TextField(verbose_name='Comment', blank=True)),
                (
                    'total_vat',
                    core_fields.MoneyField(
                        verbose_name='Total with VAT',
                        decimal_places=2, default=0, max_digits=14, null=True,
                        blank=True, editable=False,
                    )
                ),
                (
                    'total_no_vat',
                    core_fields.MoneyField(
                        verbose_name='Total without VAT',
                        decimal_places=2, default=0, max_digits=14,null=True,
                        blank=True, editable=False,
                    )
                ),
                ('additional_info', models.ForeignKey(related_name='+', on_delete=CREME_REPLACE_NULL, verbose_name='Additional Information', blank=True, to='billing.AdditionalInformation', null=True)),
                (
                    'currency',
                    models.ForeignKey(
                        verbose_name='Currency', to='creme_core.Currency',
                        related_name='+', on_delete=PROTECT,
                        # default=1,
                        default=get_default_currency_pk,
                    )
                ),
                (
                    'payment_info',
                    models.ForeignKey(
                        verbose_name='Payment information', to='billing.PaymentInformation',
                        on_delete=SET_NULL, blank=True, editable=False, null=True,
                    )
                ),
                (
                    'payment_terms',
                    models.ForeignKey(
                        verbose_name='Payment Terms', to='billing.PaymentTerms',
                        related_name='+', on_delete=CREME_REPLACE_NULL, blank=True, null=True,
                    )
                ),
                (
                    'billing_address',
                    models.ForeignKey(
                        verbose_name='Billing address',
                        to=settings.PERSONS_ADDRESS_MODEL,
                        related_name='+', on_delete=SET_NULL, editable=False, null=True,
                    )
                ),
                (
                    'shipping_address',
                    models.ForeignKey(
                        verbose_name='Shipping address',
                        to=settings.PERSONS_ADDRESS_MODEL,
                        related_name='+', on_delete=SET_NULL, editable=False, null=True,
                    )
                ),

                (
                    'status',
                    models.ForeignKey(
                        to='billing.InvoiceStatus', verbose_name='Status of invoice',
                        on_delete=CREME_REPLACE,
                        default=other_models.get_default_invoice_status_pk,
                    )
                ),
                (
                    'payment_type',
                    models.ForeignKey(
                        verbose_name='Settlement terms', to='billing.SettlementTerms',
                        on_delete=CREME_REPLACE_NULL, blank=True, null=True,
                    )
                ),
                (
                    'buyers_order_number',
                    models.CharField(
                        blank=True, max_length=100, verbose_name="Buyer's order",
                        help_text="Number of buyer's order (french legislation)",
                    )
                ),
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
                ('uuid', models.UUIDField(default=uuid4, editable=False, unique=True)),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                (
                    'color',
                    core_fields.ColorField(
                        default=core_fields.ColorField.random,
                        max_length=6, verbose_name='Color',
                    )
                ),
                ('is_default', models.BooleanField(default=False, verbose_name='Is default?')),
                ('is_custom', models.BooleanField(default=True, editable=False)),
                ('order', core_fields.BasicAutoField(editable=False, blank=True)),
                ('won', models.BooleanField(default=False, verbose_name='Won')),
                ('extra_data', models.JSONField(default=dict, editable=False)),
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
                (
                    'cremeentity_ptr',
                    models.OneToOneField(
                        parent_link=True, auto_created=True, primary_key=True, serialize=False,
                        to='creme_core.CremeEntity', on_delete=CASCADE,
                    )
                ),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                ('number', models.CharField(max_length=100, verbose_name='Number', blank=True)),
                ('issuing_date', models.DateField(null=True, verbose_name='Issuing date', blank=True)),
                ('expiration_date', models.DateField(null=True, verbose_name='Expiration date', blank=True)),
                (
                    'discount',
                    BillingDiscountField(
                        default=Decimal('0'), verbose_name='Overall discount', max_digits=10, decimal_places=2,
                    )
                ),
                ('comment', models.TextField(verbose_name='Comment', blank=True)),
                (
                    'total_vat',
                    core_fields.MoneyField(
                        verbose_name='Total with VAT',
                        decimal_places=2, default=0, max_digits=14, null=True,
                        blank=True, editable=False,
                    )
                ),
                (
                    'total_no_vat',
                    core_fields.MoneyField(
                        verbose_name='Total without VAT',
                        decimal_places=2, default=0, max_digits=14,null=True,
                        blank=True, editable=False,
                    )
                ),
                (
                    'additional_info',
                    models.ForeignKey(
                        verbose_name='Additional Information', to='billing.AdditionalInformation',
                        related_name='+', on_delete=CREME_REPLACE_NULL, blank=True, null=True,
                    )
                ),
                (
                    'currency',
                    models.ForeignKey(
                        verbose_name='Currency', to='creme_core.Currency',
                        related_name='+', on_delete=PROTECT,
                        # default=1,
                        default=get_default_currency_pk,
                    )
                ),
                (
                    'payment_terms',
                    models.ForeignKey(
                        verbose_name='Payment Terms', to='billing.PaymentTerms',
                        related_name='+', on_delete=CREME_REPLACE_NULL, blank=True, null=True,
                    )
                ),
                (
                    'payment_info',
                    models.ForeignKey(
                        verbose_name='Payment information', to='billing.PaymentInformation',
                        on_delete=SET_NULL, blank=True, editable=False, null=True,
                    )
                ),
                (
                    'payment_type',
                    models.ForeignKey(
                        verbose_name='Settlement terms', to='billing.settlementterms',
                        blank=True, null=True, on_delete=CREME_REPLACE_NULL,
                    )
                ),
                (
                    'billing_address',
                    models.ForeignKey(
                        verbose_name='Billing address',
                        to=settings.PERSONS_ADDRESS_MODEL,
                        related_name='+', on_delete=SET_NULL, editable=False, null=True,
                    )
                ),
                (
                    'shipping_address',
                    models.ForeignKey(
                        verbose_name='Shipping address',
                        to=settings.PERSONS_ADDRESS_MODEL,
                        related_name='+', on_delete=SET_NULL, editable=False, null=True,
                    )
                ),

                ('acceptation_date', models.DateField(null=True, verbose_name='Acceptation date', blank=True)),
                (
                    'status',
                    models.ForeignKey(
                        to='billing.QuoteStatus', verbose_name='Status of quote',
                        on_delete=CREME_REPLACE,
                        default=other_models.get_default_quote_status_pk,
                    )
                ),
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
                ('uuid', models.UUIDField(default=uuid4, editable=False, unique=True)),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                (
                    'color',
                    core_fields.ColorField(
                        default=core_fields.ColorField.random,
                        max_length=6, verbose_name='Color',
                    )
                ),
                ('is_default', models.BooleanField(default=False, verbose_name='Is default?')),
                ('is_custom', models.BooleanField(default=True, editable=False)),
                ('order', core_fields.BasicAutoField(editable=False, blank=True)),
                ('extra_data', models.JSONField(default=dict, editable=False)),
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
                (
                    'cremeentity_ptr',
                    models.OneToOneField(
                        parent_link=True, auto_created=True, primary_key=True, serialize=False,
                        to='creme_core.CremeEntity', on_delete=CASCADE,
                    )
                ),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                ('number', models.CharField(max_length=100, verbose_name='Number', blank=True)),
                ('issuing_date', models.DateField(null=True, verbose_name='Issuing date', blank=True)),
                ('expiration_date', models.DateField(null=True, verbose_name='Expiration date', blank=True)),
                (
                    'discount',
                    BillingDiscountField(
                        default=Decimal('0'), verbose_name='Overall discount', max_digits=10, decimal_places=2,
                    )
                ),
                ('comment', models.TextField(verbose_name='Comment', blank=True)),
                (
                    'total_vat',
                    core_fields.MoneyField(
                        verbose_name='Total with VAT',
                        decimal_places=2, default=0, max_digits=14, null=True,
                        blank=True, editable=False,
                    )
                ),
                (
                    'total_no_vat',
                    core_fields.MoneyField(
                        verbose_name='Total without VAT',
                        decimal_places=2, default=0, max_digits=14, null=True,
                        blank=True, editable=False,
                    )
                ),
                (
                    'additional_info',
                    models.ForeignKey(
                        verbose_name='Additional Information', to='billing.AdditionalInformation',
                        related_name='+', on_delete=CREME_REPLACE_NULL, blank=True, null=True,
                    )
                ),
                (
                    'currency',
                    models.ForeignKey(
                        verbose_name='Currency', to='creme_core.Currency',
                        related_name='+', on_delete=PROTECT,
                        # default=1,
                        default=get_default_currency_pk,
                    )
                ),
                (
                    'payment_terms',
                    models.ForeignKey(
                        verbose_name='Payment Terms', to='billing.PaymentTerms',
                        related_name='+', on_delete=CREME_REPLACE_NULL, blank=True, null=True,
                    )
                ),
                (
                    'payment_info',
                    models.ForeignKey(
                        verbose_name='Payment information', to='billing.PaymentInformation',
                        on_delete=SET_NULL, blank=True, editable=False, null=True,
                    )
                ),
                (
                    'payment_type',
                    models.ForeignKey(
                        verbose_name='Settlement terms', to='billing.settlementterms',
                        blank=True, null=True, on_delete=CREME_REPLACE_NULL,
                    )
                ),
                (
                    'billing_address',
                    models.ForeignKey(
                        verbose_name='Billing address',
                        to=settings.PERSONS_ADDRESS_MODEL,
                        related_name='+', on_delete=SET_NULL, editable=False, null=True,
                    )
                ),
                (
                    'shipping_address',
                    models.ForeignKey(
                        verbose_name='Shipping address',
                        to=settings.PERSONS_ADDRESS_MODEL,
                        related_name='+', on_delete=SET_NULL, editable=False, null=True,
                    )
                ),

                (
                    'status',
                    models.ForeignKey(
                        to='billing.SalesOrderStatus', verbose_name='Status of salesorder',
                        on_delete=CREME_REPLACE,
                        default=other_models.get_default_sales_order_status_pk,
                    )
                ),
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
                ('ct', core_fields.CTypeForeignKey(to='contenttypes.ContentType')),
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
                (
                    'cremeentity_ptr',
                    models.OneToOneField(
                        parent_link=True, auto_created=True, primary_key=True, serialize=False,
                        to='creme_core.CremeEntity', on_delete=CASCADE,
                    )
                ),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                ('number', models.CharField(max_length=100, verbose_name='Number', blank=True)),
                ('issuing_date', models.DateField(null=True, verbose_name='Issuing date', blank=True)),
                ('expiration_date', models.DateField(null=True, verbose_name='Expiration date', blank=True)),
                (
                    'discount',
                    BillingDiscountField(
                        default=Decimal('0'), verbose_name='Overall discount', max_digits=10, decimal_places=2,
                    )
                ),
                ('comment', models.TextField(verbose_name='Comment', blank=True)),
                (
                    'total_vat',
                    core_fields.MoneyField(
                        verbose_name='Total with VAT',
                        decimal_places=2, default=0, max_digits=14, null=True,
                        blank=True, editable=False,
                    )
                ),
                (
                    'total_no_vat',
                    core_fields.MoneyField(
                        verbose_name='Total without VAT',
                        decimal_places=2, default=0, max_digits=14, null=True,
                        blank=True, editable=False,
                    )
                ),
                (
                    'additional_info',
                    models.ForeignKey(
                        verbose_name='Additional Information', to='billing.AdditionalInformation',
                        related_name='+', on_delete=CREME_REPLACE_NULL, blank=True, null=True,
                    )
                ),
                (
                    'currency',
                    models.ForeignKey(
                        verbose_name='Currency', to='creme_core.Currency',
                        related_name='+', on_delete=PROTECT,
                        # default=1,
                        default=get_default_currency_pk,
                    )
                ),
                (
                    'payment_terms',
                    models.ForeignKey(
                        verbose_name='Payment Terms', to='billing.PaymentTerms',
                        related_name='+', on_delete=CREME_REPLACE_NULL, blank=True, null=True,
                    )
                ),
                (
                    'payment_info',
                    models.ForeignKey(
                        verbose_name='Payment information', to='billing.PaymentInformation',
                        on_delete=SET_NULL, blank=True, editable=False, null=True,
                    )
                ),
                (
                    'payment_type',
                    models.ForeignKey(
                        verbose_name='Settlement terms', to='billing.settlementterms',
                        blank=True, null=True, on_delete=CREME_REPLACE_NULL,
                    )
                ),
                (
                    'billing_address',
                    models.ForeignKey(
                        verbose_name='Billing address',
                        to=settings.PERSONS_ADDRESS_MODEL,
                        related_name='+', on_delete=SET_NULL, editable=False, null=True,
                    )
                ),
                (
                    'shipping_address',
                    models.ForeignKey(
                        verbose_name='Shipping address',
                        to=settings.PERSONS_ADDRESS_MODEL,
                        related_name='+', on_delete=SET_NULL, editable=False, null=True,
                    )
                ),

                ('status_id', models.PositiveIntegerField(editable=False)),
                ('ct', core_fields.CTypeForeignKey(editable=False, to='contenttypes.ContentType')),
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
                (
                    'cremeentity_ptr',
                    models.OneToOneField(
                        parent_link=True, auto_created=True, primary_key=True, serialize=False,
                        to='creme_core.CremeEntity', on_delete=CASCADE,
                    )
                ),
                ('on_the_fly_item', models.CharField(max_length=100, null=True, verbose_name='On-the-fly line')),
                ('comment', models.TextField(verbose_name='Comment', blank=True)),
                (
                    'quantity',
                    models.DecimalField(
                        verbose_name='Quantity',
                        default=Decimal('1.00'), max_digits=10, decimal_places=2,
                    )
                ),
                (
                    'unit_price',
                    models.DecimalField(
                        verbose_name='Unit price',
                        default=Decimal('0'), max_digits=10, decimal_places=2,
                    )
                ),
                ('unit', models.CharField(max_length=100, verbose_name='Unit', blank=True)),
                (
                    'discount',
                    models.DecimalField(
                        verbose_name='Discount',
                        default=Decimal('0'), max_digits=10, decimal_places=2,
                    )
                ),
                (
                    'discount_unit',
                    models.PositiveIntegerField(
                        default=1,
                        choices=[(1, 'Percent'), (2, 'Amount per line'), (3, 'Amount per unit')],
                        verbose_name='Discount Unit',
                    )
                ),
                (
                    'vat_value',
                    models.ForeignKey(
                        to='creme_core.Vat', verbose_name='VAT', on_delete=PROTECT,
                        # default=1,
                        default=get_default_vat_pk,
                    )
                ),
                ('order', models.PositiveIntegerField(default=0, editable=False)),
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
                (
                    'cremeentity_ptr',
                    models.OneToOneField(
                        parent_link=True, auto_created=True, primary_key=True, serialize=False,
                        to='creme_core.CremeEntity', on_delete=CASCADE,
                    )
                ),
                ('on_the_fly_item', models.CharField(max_length=100, null=True, verbose_name='On-the-fly line')),
                ('comment', models.TextField(verbose_name='Comment', blank=True)),
                (
                    'quantity',
                    models.DecimalField(
                        verbose_name='Quantity',
                        default=Decimal('1.00'), max_digits=10, decimal_places=2,
                    )
                ),
                (
                    'unit_price',
                    models.DecimalField(
                        verbose_name='Unit price',
                        default=Decimal('0'), max_digits=10, decimal_places=2,
                    )
                ),
                (
                    'unit',
                    models.CharField(max_length=100, verbose_name='Unit', blank=True)
                ),
                (
                    'discount',
                    models.DecimalField(
                        verbose_name='Discount',
                        default=Decimal('0'), max_digits=10, decimal_places=2,
                    )
                ),
                (
                    'discount_unit',
                    models.PositiveIntegerField(
                        default=1,
                        choices=[(1, 'Percent'), (2, 'Amount per line'), (3, 'Amount per unit')],
                        verbose_name='Discount Unit',
                    )
                ),
                (
                    'vat_value',
                    models.ForeignKey(
                        to='creme_core.Vat', verbose_name='VAT', on_delete=PROTECT,
                        # default=1,
                        default=get_default_vat_pk,
                    )
                ),
                ('order', models.PositiveIntegerField(default=0, editable=False)),
            ],
            options={
                'swappable': 'BILLING_SERVICE_LINE_MODEL',
                'ordering': ('created',),
                'verbose_name': 'Service line',
                'verbose_name_plural': 'Service lines',
            },
            bases=('creme_core.cremeentity',),
        ),
        migrations.CreateModel(
            name='ExporterConfigItem',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                (
                    'content_type',
                    core_fields.CTypeOneToOneField(on_delete=CASCADE, to='contenttypes.ContentType')
                ),
                ('engine_id', models.CharField(max_length=80)),
                ('flavour_id', models.CharField(max_length=80, blank=True)),
            ],
        ),
    ]
