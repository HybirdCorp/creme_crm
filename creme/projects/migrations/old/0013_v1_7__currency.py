# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.db.models.deletion import PROTECT


class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0012_v1_7__colorfields'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='currency',
            field=models.ForeignKey(related_name='+', on_delete=PROTECT, default=1,
                                    verbose_name='Currency', to='creme_core.Currency',
                                   ),
        ),
    ]
