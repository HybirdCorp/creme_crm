# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        # ('creme_core', '0042_v1_8__set_version'),
        ('creme_core', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='relation',
            name='entity_type',
        ),
        migrations.RemoveField(
            model_name='relation',
            name='header_filter_search_field',
        ),
        migrations.RemoveField(
            model_name='relation',
            name='is_deleted',
        ),
        migrations.RemoveField(
            model_name='relation',
            name='modified',
        ),
    ]
