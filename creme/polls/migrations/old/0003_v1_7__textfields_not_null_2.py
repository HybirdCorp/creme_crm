# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('polls', '0002_v1_7__textfields_not_null_1'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pollcampaign',
            name='goal',
            field=models.TextField(default='', verbose_name='Goal of the campaign', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='pollformsection',
            name='body',
            field=models.TextField(default='', verbose_name='Section body', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='pollreplysection',
            name='body',
            field=models.TextField(default='', verbose_name='Section body', blank=True),
            preserve_default=False,
        ),
    ]
