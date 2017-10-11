# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0005_v1_6__add_fieldsconfig'),
    ]

    operations = [
        migrations.AddField(
            model_name='searchconfigitem',
            name='role',
            field=models.ForeignKey(default=None, verbose_name='Related role', to='creme_core.UserRole', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='searchconfigitem',
            name='superuser',
            field=models.BooleanField(default=False, verbose_name='related to superusers', editable=False),
            preserve_default=True,
        ),
    ]
