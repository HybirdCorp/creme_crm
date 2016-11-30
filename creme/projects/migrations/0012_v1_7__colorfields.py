# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations

from creme.creme_core.models.fields import ColorField


class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0011_v1_7__charfields_not_null_2'),
    ]

    operations = [
        migrations.AlterField(
            model_name='projectstatus',
            name='color_code',
            field=ColorField(max_length=6, verbose_name='Color', blank=True),
        ),
        migrations.AlterField(
            model_name='taskstatus',
            name='color_code',
            field=ColorField(max_length=6, verbose_name='Color', blank=True),
        ),
    ]
