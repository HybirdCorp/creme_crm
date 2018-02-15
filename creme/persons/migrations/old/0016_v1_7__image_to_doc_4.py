# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('persons', '0015_v1_7__image_to_doc_3'),
    ]

    run_before = [
        ('documents', '0009_v1_7__image_to_doc_4'),
    ]

    operations = [
        migrations.RenameField(
            model_name='contact',
            old_name='image_tmp',
            new_name='image',
        ),
        migrations.RenameField(
            model_name='organisation',
            old_name='image_tmp',
            new_name='image',
        ),
    ]
