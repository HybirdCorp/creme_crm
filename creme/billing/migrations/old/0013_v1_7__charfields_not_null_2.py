# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('billing', '0012_v1_7__charfields_not_null_1'),
    ]

    operations = [
        migrations.AlterField(
            model_name='creditnote',
            name='number',
            field=models.CharField(default='', max_length=100, verbose_name='Number', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='invoice',
            name='number',
            field=models.CharField(default='', max_length=100, verbose_name='Number', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='paymentinformation',
            name='account_number',
            field=models.CharField(default='', max_length=12, verbose_name='Account number', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='paymentinformation',
            name='bank_code',
            field=models.CharField(default='', max_length=12, verbose_name='Bank code', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='paymentinformation',
            name='banking_domiciliation',
            field=models.CharField(default='', max_length=200, verbose_name='Banking domiciliation', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='paymentinformation',
            name='counter_code',
            field=models.CharField(default='', max_length=12, verbose_name='Counter code', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='paymentinformation',
            name='iban',
            field=models.CharField(default='', max_length=100, verbose_name='IBAN', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='paymentinformation',
            name='rib_key',
            field=models.CharField(default='', max_length=12, verbose_name='RIB key', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='productline',
            name='on_the_fly_item',
            field=models.CharField(max_length=100, null=True, verbose_name='On-the-fly line'),
        ),
        migrations.AlterField(
            model_name='productline',
            name='unit',
            field=models.CharField(default='', max_length=100, verbose_name='Unit', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='quote',
            name='number',
            field=models.CharField(default='', max_length=100, verbose_name='Number', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='salesorder',
            name='number',
            field=models.CharField(default='', max_length=100, verbose_name='Number', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='serviceline',
            name='on_the_fly_item',
            field=models.CharField(max_length=100, null=True, verbose_name='On-the-fly line'),
        ),
        migrations.AlterField(
            model_name='serviceline',
            name='unit',
            field=models.CharField(default='', max_length=100, verbose_name='Unit', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='templatebase',
            name='number',
            field=models.CharField(default='', max_length=100, verbose_name='Number', blank=True),
            preserve_default=False,
        ),
    ]
