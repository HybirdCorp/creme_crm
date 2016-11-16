# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('documents',      '0009_v1_7__image_to_doc_4'),
        ('media_managers', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='image',
            name='categories',
        ),
        migrations.RemoveField(
            model_name='image',
            name='cremeentity_ptr',
        ),
        migrations.DeleteModel(
            name='Image',
        ),
        migrations.DeleteModel(
            name='MediaCategory',
        ),
    ]
