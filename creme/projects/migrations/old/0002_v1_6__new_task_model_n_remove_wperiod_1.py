# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):
    dependencies = [
        ('projects',   '0001_initial'),
        ('creme_core', '0004_v1_6__convert_user_FKs_n_remove_old_teamM2M'),
        ('persons',    '0002_v1_6__convert_user_FKs'),
        ('activities', '0001_initial'),
    ]

    operations = [
        # Step 1.1: FK to CremeEntity ; it is not the primary key yet (not unique etc..)
        migrations.AddField(
            model_name='projecttask',
            name='cremeentity_ptr',
            field=models.OneToOneField(
                # NB: temporarily commented
                #parent_link=True, auto_created=True, primary_key=True,
                serialize=False, to='creme_core.CremeEntity',
                null=True, default=None, # temporary values
               ),
            preserve_default=True,
        ),
        # 'title' field is added, with temporary value
        migrations.AddField(
            model_name='projecttask',
            name='title',
            field=models.CharField(max_length=100, verbose_name='Title',
                                   default='TMP',
                                  ),
            preserve_default=True,
        ),

        # Other fields are added
        migrations.AddField(
            model_name='projecttask',
            name='start',
            field=models.DateTimeField(null=True, verbose_name='Start', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='projecttask',
            name='end',
            field=models.DateTimeField(null=True, verbose_name='End', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='projecttask',
            name='duration',
            field=models.PositiveIntegerField(null=True, verbose_name='Duration (in hours)', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='projecttask',
            name='description',
            field=models.TextField(null=True, verbose_name='Description', blank=True),
            preserve_default=True,
        ),
    ]
