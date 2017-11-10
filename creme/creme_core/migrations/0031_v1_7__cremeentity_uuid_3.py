# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0030_v1_7__cremeentity_uuid_2'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cremeentity',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, unique=True, editable=False),
        ),
    ]
