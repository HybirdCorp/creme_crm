# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('recurrents', '0002_v1_7__name_not_null_1'),
    ]

    operations = [
        migrations.AlterField(
            model_name='recurrentgenerator',
            name='name',
            field=models.CharField(default='', max_length=100, verbose_name='Name of the generator', blank=True),
            preserve_default=False,
        ),
    ]
