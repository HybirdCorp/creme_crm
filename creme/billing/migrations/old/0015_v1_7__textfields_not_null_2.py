# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('billing', '0014_v1_7__textfields_not_null_1'),
    ]

    operations = [
        migrations.AlterField(
            model_name='additionalinformation',
            name='description',
            field=models.TextField(default='', verbose_name='Description', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='creditnote',
            name='comment',
            field=models.TextField(default='', verbose_name='Comment', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='invoice',
            name='comment',
            field=models.TextField(default='', verbose_name='Comment', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='paymentinformation',
            name='bic',
            field=models.CharField(default='', max_length=100, verbose_name='BIC', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='paymentterms',
            name='description',
            field=models.TextField(default='', verbose_name='Description', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='productline',
            name='comment',
            field=models.TextField(default='', verbose_name='Comment', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='quote',
            name='comment',
            field=models.TextField(default='', verbose_name='Comment', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='salesorder',
            name='comment',
            field=models.TextField(default='', verbose_name='Comment', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='serviceline',
            name='comment',
            field=models.TextField(default='', verbose_name='Comment', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='templatebase',
            name='comment',
            field=models.TextField(default='', verbose_name='Comment', blank=True),
            preserve_default=False,
        ),
    ]
