# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations

from creme.creme_core.models.fields import ColorField


class Migration(migrations.Migration):
    dependencies = [
        ('activities', '0009_v1_7__textfields_not_null_2'),
    ]

    operations = [
        migrations.AlterField(
            model_name='calendar',
            name='color',
            field=ColorField(max_length=6, verbose_name='Color'),
        ),
    ]
