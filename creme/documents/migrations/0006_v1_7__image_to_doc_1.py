# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('documents', '0005_v1_7__doc_categories'),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='filedata_tmp',
            field=models.FileField(max_length=500, null=True, verbose_name='File', upload_to=b'upload/documents'),
        ),
    ]
