# -*- coding: utf-8 -*-

from datetime import datetime

from django.db import migrations, models
from django.utils.timezone import make_aware, utc

EPOCH = make_aware(datetime(year=1970, month=1, day=1), utc)


class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='projecttask',
            name='duration',
            field=models.PositiveIntegerField(default=0, verbose_name='Duration (in hours)'),
            # preserve_default=False,
        ),
        migrations.AlterField(
            model_name='projecttask',
            name='end',
            field=models.DateTimeField(default=EPOCH, verbose_name='End'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='projecttask',
            name='start',
            field=models.DateTimeField(default=EPOCH, verbose_name='Start'),
            preserve_default=False,
        ),
    ]
