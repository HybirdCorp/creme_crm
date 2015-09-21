# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):
    dependencies = [
        ('persons', '0005_v1_6__emails_length'),
    ]

    operations = [
        migrations.AddField(
            model_name='contact',
            name='full_position',
            field=models.CharField(max_length=500, null=True, verbose_name='Detailed position', blank=True),
        ),
    ]
