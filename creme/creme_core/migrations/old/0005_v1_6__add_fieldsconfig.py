# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

import creme.creme_core.models.fields


class Migration(migrations.Migration):
    dependencies = [
        ('contenttypes', '0001_initial'),
        ('creme_core', '0004_v1_6__convert_user_FKs_n_remove_old_teamM2M'),
    ]

    operations = [
        migrations.CreateModel(
            name='FieldsConfig',
            fields=[
                ('content_type', creme.creme_core.models.fields.CTypeForeignKey(primary_key=True, serialize=False, editable=False, to='contenttypes.ContentType')),
                ('raw_descriptions', models.TextField(editable=False)),
            ],
            options={},
            bases=(models.Model,),
        ),
    ]
