# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('opportunities', '0002_v1_7__reference_not_null_1'),
    ]

    operations = [
        migrations.AlterField(
            model_name='opportunity',
            name='reference',
            field=models.CharField(default='', max_length=100, verbose_name='Reference', blank=True),
            preserve_default=False,
        ),
    ]
