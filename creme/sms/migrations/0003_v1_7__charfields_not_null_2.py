# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('sms', '0002_v1_7__charfields_not_null_1'),
    ]

    operations = [
        migrations.AlterField(
            model_name='message',
            name='status_message',
            field=models.CharField(default='', max_length=100, verbose_name='Full state', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='recipient',
            name='phone',
            field=models.CharField(default='', max_length=100, verbose_name='Number', blank=True),
            preserve_default=False,
        ),
    ]
