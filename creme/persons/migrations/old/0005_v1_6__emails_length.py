# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):
    dependencies = [
        ('persons', '0004_v1_6__fk_on_delete_set'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contact',
            name='email',
            field=models.EmailField(max_length=254, null=True, verbose_name='Email address', blank=True),
        ),
        migrations.AlterField(
            model_name='organisation',
            name='email',
            field=models.EmailField(max_length=254, null=True, verbose_name='Email address', blank=True),
        ),
    ]
