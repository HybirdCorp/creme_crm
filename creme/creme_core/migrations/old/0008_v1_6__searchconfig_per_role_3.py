# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0007_v1_6__searchconfig_per_role_2'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='searchconfigitem',
            unique_together=set([('content_type', 'role', 'superuser')]),
        ),
        migrations.RemoveField(
            model_name='searchconfigitem',
            name='user',
        ),
    ]
