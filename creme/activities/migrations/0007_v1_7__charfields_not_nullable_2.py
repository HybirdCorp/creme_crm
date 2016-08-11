# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('activities', '0006_v1_7__charfields_not_nullable_1'),
    ]

    operations = [
        migrations.AlterField(
            model_name='activity',
            name='place',
            field=models.CharField(default='', max_length=500, verbose_name='Activity place', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='calendar',
            name='color',
            field=models.CharField(default='c1d9ec', max_length=100, verbose_name='Color'),
            preserve_default=False,
        ),
    ]
