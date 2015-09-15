# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):
    dependencies = [
        ('commercial', '0003_v1_6__django18_hints'),
    ]

    operations = [
        migrations.AlterField(
            model_name='marketsegment',
            name='property_type',
            field=models.ForeignKey(editable=False, to='creme_core.CremePropertyType', null=True),
        ),
    ]
