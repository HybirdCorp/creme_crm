# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('documents', '0011_v1_7__mime_type_2'),
    ]

    operations = [
        migrations.AlterField(
            model_name='documentcategory',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, unique=True, editable=False),
        ),
    ]
