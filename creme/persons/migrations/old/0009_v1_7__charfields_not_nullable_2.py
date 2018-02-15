# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import creme.creme_core.models.fields


class Migration(migrations.Migration):
    dependencies = [
        ('persons', '0008_v1_7__charfields_not_nullable_1'),
    ]

    operations = [
        migrations.AlterField(
            model_name='address',
            name='address',
            field=models.TextField(default='', verbose_name='Address', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='address',
            name='city',
            field=models.CharField(default='', max_length=100, verbose_name='City', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='address',
            name='country',
            field=models.CharField(default='', max_length=40, verbose_name='Country', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='address',
            name='department',
            field=models.CharField(default='', max_length=100, verbose_name='Department', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='address',
            name='name',
            field=models.CharField(default='', max_length=100, verbose_name='Name', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='address',
            name='po_box',
            field=models.CharField(default='', max_length=50, verbose_name='PO box', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='address',
            name='state',
            field=models.CharField(default='', max_length=100, verbose_name='State', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='address',
            name='zipcode',
            field=models.CharField(default='', max_length=100, verbose_name='Zip code', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='contact',
            name='description',
            field=models.TextField(default='', verbose_name='Description', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='contact',
            name='email',
            field=models.EmailField(default='', max_length=254, verbose_name='Email address', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='contact',
            name='first_name',
            field=models.CharField(default='', max_length=100, verbose_name='First name', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='contact',
            name='full_position',
            field=models.CharField(default='', max_length=500, verbose_name='Detailed position', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='contact',
            name='mobile',
            field=creme.creme_core.models.fields.PhoneField(default='', max_length=100, verbose_name='Mobile', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='contact',
            name='phone',
            field=creme.creme_core.models.fields.PhoneField(default='', max_length=100, verbose_name='Phone number', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='contact',
            name='skype',
            field=models.CharField(default='', max_length=100, verbose_name=b'Skype', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='contact',
            name='url_site',
            field=models.URLField(default='', max_length=500, verbose_name='Web Site', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='organisation',
            name='annual_revenue',
            field=models.CharField(default='', max_length=100, verbose_name='Annual revenue', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='organisation',
            name='description',
            field=models.TextField(default='', verbose_name='Description', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='organisation',
            name='email',
            field=models.EmailField(default='', max_length=254, verbose_name='Email address', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='organisation',
            name='fax',
            field=models.CharField(default='', max_length=100, verbose_name='Fax', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='organisation',
            name='naf',
            field=models.CharField(default='', max_length=100, verbose_name='NAF code', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='organisation',
            name='phone',
            field=creme.creme_core.models.fields.PhoneField(default='', max_length=100, verbose_name='Phone number', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='organisation',
            name='rcs',
            field=models.CharField(default='', max_length=100, verbose_name='RCS/RM', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='organisation',
            name='siren',
            field=models.CharField(default='', max_length=100, verbose_name='SIREN', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='organisation',
            name='siret',
            field=models.CharField(default='', max_length=100, verbose_name='SIRET', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='organisation',
            name='tvaintra',
            field=models.CharField(default='', max_length=100, verbose_name='VAT number', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='organisation',
            name='url_site',
            field=models.URLField(default='', max_length=500, verbose_name='Web Site', blank=True),
            preserve_default=False,
        ),
    ]
