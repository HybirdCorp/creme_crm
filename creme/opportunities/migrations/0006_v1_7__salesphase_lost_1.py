# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('opportunities', '0005_v1_7__description_not_null_2'),
    ]

    operations = [
        migrations.AddField(
            model_name='salesphase',
            name='lost',
            field=models.BooleanField(default=False, verbose_name='Lost'),
        ),
    ]
