# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from decimal import Decimal

from django.db import models, migrations
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('billing', '0004_v1_6__make_base_abstract_3'),
    ]

    operations = [
        # Step 1: fields of base are added in final classes (Invoice, Quote, SalesOrder, CreditNote, TemplateBase)

        # Step 1.1: FK to CremeEntity
        migrations.AddField(
            model_name='productline',
            name='cremeentity_ptr',
            field=models.OneToOneField(
                # NB: temporarily commented
                #parent_link=True, auto_created=True, primary_key=True,
                serialize=False, to='creme_core.CremeEntity',
                null=True, default=None, # temporary values
               ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='serviceline',
            name='cremeentity_ptr',
            field=models.OneToOneField(
                # NB: temporarily commented
                #parent_link=True, auto_created=True, primary_key=True,
                serialize=False, to='creme_core.CremeEntity',
                null=True, default=None, # temporary values
               ),
            preserve_default=False,
        ),

        # Step 1.2: other fields
        migrations.AddField(
            model_name='productline',
            name='comment',
            field=models.TextField(null=True, verbose_name='Comment', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='productline',
            name='discount',
            field=models.DecimalField(default=Decimal('0'), verbose_name='Discount', max_digits=10, decimal_places=2),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='productline',
            name='discount_unit',
            field=models.PositiveIntegerField(default=1, editable=False, choices=[(1, 'Percent'), (2, 'Amount')], blank=True, null=True, verbose_name='Discount Unit'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='productline',
            name='on_the_fly_item',
            field=models.CharField(max_length=100, null=True, verbose_name='On-the-fly line', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='productline',
            name='quantity',
            field=models.DecimalField(default=Decimal('1.00'), verbose_name='Quantity', max_digits=10, decimal_places=2),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='productline',
            name='total_discount',
            field=models.BooleanField(default=False, verbose_name='Total discount ?', editable=False),
            preserve_default=True,
        ),
#        migrations.AddField(
#            model_name='productline',
#            name='type',
#            field=models.IntegerField(default=1, verbose_name='Type', editable=False, choices=[(1, 'Product'), (2, 'Service')]),
#            preserve_default=False,
#        ),
        migrations.AddField(
            model_name='productline',
            name='unit',
            field=models.CharField(max_length=100, null=True, verbose_name='Unit', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='productline',
            name='unit_price',
            field=models.DecimalField(default=Decimal('0'), verbose_name='Unit price', max_digits=10, decimal_places=2),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='productline',
            name='vat_value',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, verbose_name='VAT', blank=True, to='creme_core.Vat', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='serviceline',
            name='comment',
            field=models.TextField(null=True, verbose_name='Comment', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='serviceline',
            name='discount',
            field=models.DecimalField(default=Decimal('0'), verbose_name='Discount', max_digits=10, decimal_places=2),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='serviceline',
            name='discount_unit',
            field=models.PositiveIntegerField(default=1, editable=False, choices=[(1, 'Percent'), (2, 'Amount')], blank=True, null=True, verbose_name='Discount Unit'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='serviceline',
            name='on_the_fly_item',
            field=models.CharField(max_length=100, null=True, verbose_name='On-the-fly line', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='serviceline',
            name='quantity',
            field=models.DecimalField(default=Decimal('1.00'), verbose_name='Quantity', max_digits=10, decimal_places=2),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='serviceline',
            name='total_discount',
            field=models.BooleanField(default=False, verbose_name='Total discount ?', editable=False),
            preserve_default=True,
        ),
 #       migrations.AddField(
 #           model_name='serviceline',
 #           name='type',
 #           field=models.IntegerField(default=2, verbose_name='Type', editable=False, choices=[(1, 'Product'), (2, 'Service')]),
 #           preserve_default=False,
 #       ),
        migrations.AddField(
            model_name='serviceline',
            name='unit',
            field=models.CharField(max_length=100, null=True, verbose_name='Unit', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='serviceline',
            name='unit_price',
            field=models.DecimalField(default=Decimal('0'), verbose_name='Unit price', max_digits=10, decimal_places=2),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='serviceline',
            name='vat_value',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, verbose_name='VAT', blank=True, to='creme_core.Vat', null=True),
            preserve_default=True,
        ),
    ]

