# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('emails', '0002_v1_6__convert_user_FKs'),
    ]

    operations = [
        migrations.AlterField(
            model_name='emailsending',
            name='signature',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, editable=False, to='emails.EmailSignature', null=True, verbose_name='Signature'),
            preserve_default=True,
        ),
    ]
