# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('reports', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='reportgraph',
            old_name='report',
            new_name='linked_report',
        ),
    ]
