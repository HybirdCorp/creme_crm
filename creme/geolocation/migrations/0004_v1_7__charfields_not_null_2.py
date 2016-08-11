# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('geolocation', '0003_v1_7__charfields_not_null_1'),
    ]

    operations = [
        migrations.AlterField(
            model_name='town',
            name='country',
            field=models.CharField(default='', max_length=40, verbose_name='Country', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='town',
            name='zipcode',
            field=models.CharField(default='', max_length=100, verbose_name='Zip code', blank=True),
            preserve_default=False,
        ),
    ]
