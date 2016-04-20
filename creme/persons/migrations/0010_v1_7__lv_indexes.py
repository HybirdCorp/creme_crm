# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('persons', '0009_v1_7__charfields_not_nullable_2'),
    ]

    operations = [
        migrations.AlterIndexTogether(
            name='contact',
            index_together={('last_name', 'first_name', 'cremeentity_ptr')},
        ),
        migrations.AlterIndexTogether(
            name='organisation',
            index_together={('name', 'cremeentity_ptr')},
        ),
    ]
