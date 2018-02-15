# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('persons', '0016_v1_7__image_to_doc_4'),
    ]

    operations = [
        migrations.AddField(
            model_name='organisation',
            name='is_managed',
            field=models.BooleanField(default=False, verbose_name='Managed by Creme', editable=False),
        ),
    ]
