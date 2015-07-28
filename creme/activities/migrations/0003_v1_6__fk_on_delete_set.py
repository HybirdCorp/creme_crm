# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('activities', '0002_v1_6__convert_user_FKs'),
    ]

    operations = [
        migrations.AlterField(
            model_name='activity',
            name='status',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, verbose_name='Status', blank=True, to='activities.Status', null=True),
            preserve_default=True,
        ),
    ]
