# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import models, migrations
import django.utils.timezone

import creme.creme_core.models.fields


class Migration(migrations.Migration):
    # replaces = [
    #     ('crudity', '0001_initial'),
    #     ('crudity', '0002_v1_6__convert_user_FKs'),
    # ]

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('contenttypes', '0001_initial'),
        ('auth', '0001_initial'),
        ('creme_core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='History',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', creme.creme_core.models.fields.CreationDateTimeField(default=django.utils.timezone.now, verbose_name='Creation date', editable=False, blank=True)),
                ('action', models.CharField(max_length=100, verbose_name='Action')),
                ('source', models.CharField(max_length=100, verbose_name='Source')),
                ('description', models.TextField(null=True, verbose_name='Description', blank=True)),
                ('entity', models.ForeignKey(verbose_name='Entity', to='creme_core.CremeEntity')),
                # ('user', creme.creme_core.models.fields.CremeUserForeignKey(default=None, blank=True, to='auth.User', null=True, verbose_name='Owner')),
                ('user', creme.creme_core.models.fields.CremeUserForeignKey(default=None, blank=True, to=settings.AUTH_USER_MODEL, null=True, verbose_name='Owner')),
            ],
            options={
                'verbose_name': 'History',
                'verbose_name_plural': 'History',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='WaitingAction',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('action', models.CharField(max_length=100, verbose_name='Action')),
                ('source', models.CharField(max_length=100, verbose_name='Source')),
                ('data', models.TextField(null=True, blank=True)),
                ('subject', models.CharField(max_length=100, verbose_name='Subject')),
                ('ct', creme.creme_core.models.fields.CTypeForeignKey(verbose_name="Ressource's type", to='contenttypes.ContentType')),
                # ('user', creme.creme_core.models.fields.CremeUserForeignKey(default=None, blank=True, to='auth.User', null=True, verbose_name='Owner')),
                ('user', creme.creme_core.models.fields.CremeUserForeignKey(default=None, blank=True, to=settings.AUTH_USER_MODEL, null=True, verbose_name='Owner')),
            ],
            options={
                'verbose_name': 'Waiting action',
                'verbose_name_plural': 'Waiting actions',
            },
            bases=(models.Model,),
        ),
    ]
