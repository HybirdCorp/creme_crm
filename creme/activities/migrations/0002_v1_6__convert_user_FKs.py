# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import models, migrations

import creme.creme_core.models.fields


class Migration(migrations.Migration):
    dependencies = [
        ('activities', '0001_initial'),
        ('creme_core', '0003_v1_6__convert_old_users'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='calendar',
            name='user',
            field=creme.creme_core.models.fields.CremeUserForeignKey(verbose_name='Calendar owner', to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
    ]
