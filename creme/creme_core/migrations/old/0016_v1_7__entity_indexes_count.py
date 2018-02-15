# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0015_v1_7__create_job_models'),
    ]

    operations = [
        migrations.AlterIndexTogether(
            name='cremeentity',
            index_together={('entity_type', 'is_deleted')},
        ),
    ]
