# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('emails', '0010_v1_7__image_to_doc_3'),
    ]

    run_before = [
        ('documents', '0009_v1_7__image_to_doc_4'),
    ]

    operations = [
        migrations.RenameField(
            model_name='emailsignature',
            old_name='images_tmp',
            new_name='images',
        ),
    ]
