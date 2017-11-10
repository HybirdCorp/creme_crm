# -*- coding: utf-8 -*-
from __future__ import unicode_literals
# import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('creme_core', '0028_v1_7__customfields_uniqueness_3'),
    ]

    operations = [
        migrations.AddField(
            model_name='cremeentity',
            name='uuid',
            # field=models.UUIDField(default=uuid.uuid4, editable=False),
            field=models.UUIDField(default=None, null=True, editable=False),
        ),
    ]
