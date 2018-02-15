# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('assistants', '0003_v1_7__textfields_not_null_1'),
    ]

    operations = [
        migrations.AlterField(
            model_name='action',
            name='description',
            field=models.TextField(default='', verbose_name='Source action', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='action',
            name='expected_reaction',
            field=models.TextField(default='', verbose_name='Target action', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='alert',
            name='description',
            field=models.TextField(default='', verbose_name='Description', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='memo',
            name='content',
            field=models.TextField(default='?', verbose_name='Content'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='todo',
            name='description',
            field=models.TextField(default='', verbose_name='Description', blank=True),
            preserve_default=False,
        ),
    ]
