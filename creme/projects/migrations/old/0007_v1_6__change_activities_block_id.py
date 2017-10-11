# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


def update_block_conf(apps, schema_editor):
    apps.get_model('creme_core', 'BlockDetailviewLocation').objects \
        .filter(block_id='block_projects-working_periods') \
        .update(block_id='block_projects-task_activities')


class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0006_v1_6__resource_default_cost'),
    ]

    operations = [
        migrations.RunPython(update_block_conf),
    ]
