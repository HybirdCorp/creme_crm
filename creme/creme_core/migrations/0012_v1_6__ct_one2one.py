# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

import creme.creme_core.models.fields


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0011_v1_6__blockconfig_per_role'),
    ]

    operations = [
        migrations.AlterField(
            model_name='fieldsconfig',
            name='content_type',
            field=creme.creme_core.models.fields.CTypeOneToOneField(primary_key=True, serialize=False, editable=False, to='contenttypes.ContentType'),
        ),
    ]
