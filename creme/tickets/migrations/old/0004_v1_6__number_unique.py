# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):
    dependencies = [
        ('tickets', '0003_v1_6__populate_numbers'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ticket',
            name='number',
            field=models.PositiveIntegerField(verbose_name='Number', unique=True, editable=False),
        ),
    ]
