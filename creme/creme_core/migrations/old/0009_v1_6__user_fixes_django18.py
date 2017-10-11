# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import models, migrations


def fix_unlogged_users(apps, schema_editor):
    if settings.AUTH_USER_MODEL == 'creme_core.CremeUser':
        apps.get_model('creme_core', 'CremeUser').objects \
                                                 .filter(last_login=models.F('date_joined')) \
                                                 .update(last_login=None)


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0008_v1_6__searchconfig_per_role_3'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cremeuser',
            name='email',
            field=models.EmailField(max_length=254, verbose_name='Email address', blank=True),
        ),
        migrations.AlterField(
            model_name='cremeuser',
            name='last_login',
            field=models.DateTimeField(null=True, verbose_name='last login', blank=True),
        ),

        migrations.RunPython(fix_unlogged_users),
    ]
