# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0010_v1_6__django18_hints'),
    ]

    operations = [
        migrations.AddField(
            model_name='blockdetailviewlocation',
            name='role',
            field=models.ForeignKey(default=None, verbose_name='Related role', to='creme_core.UserRole', null=True),
        ),
        migrations.AddField(
            model_name='blockdetailviewlocation',
            name='superuser',
            field=models.BooleanField(default=False, verbose_name='related to superusers', editable=False),
        ),
    ]
