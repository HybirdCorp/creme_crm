# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('activities', '0008_v1_7__textfields_not_null_1'),
    ]

    operations = [
        migrations.AlterField(
            model_name='activity',
            name='description',
            field=models.TextField(default='', verbose_name='Description', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='activity',
            name='minutes',
            field=models.TextField(default='', verbose_name='Minutes', blank=True),
            preserve_default=False,
        ),
    ]
