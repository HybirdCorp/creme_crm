# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import models, migrations
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('persons', '0001_initial'),
        ('creme_core', '0003_v1_6__convert_old_users'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contact',
            name='is_user',
            field=models.ForeignKey(related_name='related_contact', on_delete=django.db.models.deletion.SET_NULL, blank=True, editable=False, to=settings.AUTH_USER_MODEL, null=True, verbose_name='Related user'),
            preserve_default=True,
        ),
    ]
