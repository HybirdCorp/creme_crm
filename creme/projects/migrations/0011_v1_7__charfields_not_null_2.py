# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0010_v1_7__charfields_not_null_1'),
    ]

    operations = [
        migrations.AlterField(
            model_name='project',
            name='description',
            field=models.TextField(default='', verbose_name='Description', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='projectstatus',
            name='color_code',
            field=models.CharField(default='', max_length=100, verbose_name='Color', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='projecttask',
            name='description',
            field=models.TextField(default='', verbose_name='Description', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='taskstatus',
            name='color_code',
            field=models.CharField(default='', max_length=100, verbose_name='Color', blank=True),
            preserve_default=False,
        ),
    ]
