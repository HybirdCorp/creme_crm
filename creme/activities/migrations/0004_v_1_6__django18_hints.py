# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):
    dependencies = [
        ('activities', '0003_v1_6__fk_on_delete_set'),
    ]

    operations = [
        migrations.AlterField(
            model_name='activity',
            name='calendars',
            field=models.ManyToManyField(verbose_name='Calendars', editable=False, to='activities.Calendar', blank=True),
        ),
    ]
