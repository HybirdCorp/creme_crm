# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import models, migrations


class Migration(migrations.Migration):
    dependencies = [
        ('activesync', '0002_v1_6__convert_user_FKs'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cremeclient',
            name='user',
            field=models.OneToOneField(verbose_name='Assigned to', to=settings.AUTH_USER_MODEL),
        ),
    ]
