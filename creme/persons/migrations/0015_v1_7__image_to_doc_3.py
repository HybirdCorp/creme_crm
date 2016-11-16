# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('persons', '0014_v1_7__image_to_doc_2'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='contact',
            name='image',
        ),
        migrations.RemoveField(
            model_name='organisation',
            name='image',
        ),
    ]
