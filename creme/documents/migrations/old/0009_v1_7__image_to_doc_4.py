# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('documents', '0008_v1_7__image_to_doc_3'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='document',
            name='filedata_tmp',
        ),
    ]
