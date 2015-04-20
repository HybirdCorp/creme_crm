# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):
    dependencies = [
        ('mobile', '0001_initial'),
        ('creme_core', '0003_v1_6__convert_old_users'),
    ]

    operations = [
        migrations.AlterField(
            model_name='mobilefavorite',
            name='user',
            field=models.ForeignKey(related_name='mobile_favorite', to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
    ]
