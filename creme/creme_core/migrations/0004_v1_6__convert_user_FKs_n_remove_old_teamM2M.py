# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import models, migrations
import django.db.models.deletion

import creme.creme_core.models.fields


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0003_v1_6__convert_old_users'),
    ]

    operations = [
        migrations.AlterField(
            model_name='blockmypagelocation',
            name='user',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL, null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='blockstate',
            name='user',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='cremeentity',
            name='user',
            field=creme.creme_core.models.fields.CremeUserForeignKey(verbose_name='Owner user', to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='entityfilter',
            name='user',
            field=creme.creme_core.models.fields.CremeUserForeignKey(verbose_name='Owner user', blank=True, to=settings.AUTH_USER_MODEL, null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='headerfilter',
            name='user',
            field=creme.creme_core.models.fields.CremeUserForeignKey(verbose_name='Owner user', blank=True, to=settings.AUTH_USER_MODEL, null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='historyline',
            name='entity_owner',
            field=creme.creme_core.models.fields.CremeUserForeignKey(to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='preferedmenuitem',
            name='user',
            field=models.ForeignKey(verbose_name='User', to=settings.AUTH_USER_MODEL, null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='relation',
            name='user',
            field=creme.creme_core.models.fields.CremeUserForeignKey(verbose_name='Owner user', to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='searchconfigitem',
            name='user',
            field=models.ForeignKey(verbose_name='Related user', to=settings.AUTH_USER_MODEL, null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='settingvalue',
            name='user',
            field=models.ForeignKey(blank=True, to=settings.AUTH_USER_MODEL, null=True),
            preserve_default=True,
        ),
        # Remove TeamM2M table
        migrations.RemoveField(
            model_name='teamm2m',
            name='team',
        ),
        migrations.RemoveField(
            model_name='teamm2m',
            name='teammate',
        ),
        migrations.DeleteModel(
            name='TeamM2M',
        ),
    ]

    if settings.TESTS_ON:
        operations.extend([
            migrations.AlterField(
                model_name='fakecontact',
                name='is_user',
                field=models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.SET_NULL, blank=True, editable=False, to=settings.AUTH_USER_MODEL, null=True, verbose_name='Related user'),
                preserve_default=True,
            ),
        ])