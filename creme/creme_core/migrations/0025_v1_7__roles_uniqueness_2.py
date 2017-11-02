# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0024_v1_7__roles_uniqueness_1'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userrole',
            name='name',
            field=models.CharField(unique=True, max_length=100, verbose_name='Name'),
        ),
    ]
