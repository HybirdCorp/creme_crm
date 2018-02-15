# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0019_v1_7__properties_uniqueness_1'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='cremeproperty',
            unique_together={('type', 'creme_entity')},
        ),
    ]
