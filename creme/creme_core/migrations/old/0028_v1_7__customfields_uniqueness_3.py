# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0027_v1_7__customfields_uniqueness_2'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customfield',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, unique=True, editable=False),
        ),
        migrations.AlterUniqueTogether(
            name='customfield',
            unique_together={('content_type', 'name')},
        ),
    ]
