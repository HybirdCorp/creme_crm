# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('commercial', '0006_v1_7__textfields_not_null_1'),
    ]

    operations = [
        migrations.AlterField(
            model_name='act',
            name='goal',
            field=models.TextField(default='', verbose_name='Goal of the action', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='commercialapproach',
            name='description',
            field=models.TextField(default='', verbose_name='Description', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='marketsegmentdescription',
            name='place',
            field=models.TextField(default='', verbose_name='Place', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='marketsegmentdescription',
            name='price',
            field=models.TextField(default='', verbose_name='Price', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='marketsegmentdescription',
            name='product',
            field=models.TextField(default='', verbose_name='Product', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='marketsegmentdescription',
            name='promotion',
            field=models.TextField(default='', verbose_name='Promotion', blank=True),
            preserve_default=False,
        ),
    ]
