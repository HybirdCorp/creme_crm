# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('documents', '0003_v1_7__textfields_not_null_1'),
    ]

    operations = [
        migrations.AlterField(
            model_name='document',
            name='description',
            field=models.TextField(default='', verbose_name='Description', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='folder',
            name='description',
            field=models.TextField(default='', verbose_name='Description', blank=True),
            preserve_default=False,
        ),
    ]
