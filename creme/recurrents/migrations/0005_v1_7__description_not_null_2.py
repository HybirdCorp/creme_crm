# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('recurrents', '0004_v1_7__description_not_null_1'),
    ]

    operations = [
        migrations.AlterField(
            model_name='recurrentgenerator',
            name='description',
            field=models.TextField(default='', verbose_name='Description', blank=True),
            preserve_default=False,
        ),
    ]
