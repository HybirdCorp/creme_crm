# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0017_v1_7__user_tz_n_theme'),
    ]

    operations = [
        migrations.AddField(
            model_name='cremeuser',
            name='json_settings',
            field=models.TextField(default='{}', editable=False),
        ),
    ]
