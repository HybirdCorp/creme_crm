# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0009_v1_6__user_fixes_django18'),
    ]

    operations = [
        migrations.AlterField(
            model_name='historyconfigitem',
            name='relation_type',
            field=models.OneToOneField(to='creme_core.RelationType'),
        ),
        migrations.AlterField(
            model_name='relationblockitem',
            name='relation_type',
            field=models.OneToOneField(verbose_name='Related type of relationship', to='creme_core.RelationType'),
        ),
    ]
