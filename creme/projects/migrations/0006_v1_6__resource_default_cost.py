# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import models, migrations


class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0005_v1_6__new_task_model_n_remove_wperiod_4'),
    ]

    operations = [
        migrations.AlterField(
            model_name='resource',
            name='hourly_cost',
            field=models.PositiveIntegerField(default=0, verbose_name='Hourly cost'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='resource',
            name='linked_contact',
            field=models.ForeignKey(editable=False, to=settings.PERSONS_CONTACT_MODEL, verbose_name='Contact'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='resource',
            name='task',
            field=models.ForeignKey(related_name='resources_set', editable=False, to='projects.ProjectTask', verbose_name='Task'),
            preserve_default=True,
        ),
    ]
