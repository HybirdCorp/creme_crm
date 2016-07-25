# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('persons', '0011_v1_7__fax_not_nullable_1'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contact',
            name='fax',
            field=models.CharField(default='', max_length=100, verbose_name='Fax', blank=True),
            preserve_default=False,
        ),
    ]
