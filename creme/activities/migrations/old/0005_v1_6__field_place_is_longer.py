# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):
    dependencies = [
        ('activities', '0004_v_1_6__django18_hints'),
    ]

    operations = [
        migrations.AlterField(
            model_name='activity',
            name='place',
            field=models.CharField(max_length=500, null=True, verbose_name='Activity place', blank=True),
        ),
    ]
