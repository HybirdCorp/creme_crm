# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings

import creme.creme_core.models.fields


class Migration(migrations.Migration):
    dependencies = [
        ('assistants', '0001_initial'),
        ('creme_core', '0003_v1_6__convert_old_users'),
    ]

    operations = [
        migrations.AlterField(
            model_name='action',
            name='user',
            field=creme.creme_core.models.fields.CremeUserForeignKey(verbose_name='Owner user', to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='alert',
            name='user',
            field=creme.creme_core.models.fields.CremeUserForeignKey(verbose_name='Owner user', to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='memo',
            name='user',
            field=creme.creme_core.models.fields.CremeUserForeignKey(verbose_name='Owner user', to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='todo',
            name='user',
            field=creme.creme_core.models.fields.CremeUserForeignKey(verbose_name='Owner user', to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='usermessage',
            name='recipient',
            field=creme.creme_core.models.fields.CremeUserForeignKey(related_name='received_assistants_messages_set', verbose_name='Recipient', to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='usermessage',
            name='sender',
            field=creme.creme_core.models.fields.CremeUserForeignKey(related_name='sent_assistants_messages_set', verbose_name='Sender', to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
    ]
