# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import models, migrations
from django.db.models.deletion import CASCADE
from django.utils.timezone import now

import creme.creme_core.models.fields

import creme.activesync.models.active_sync
import creme.activesync.utils


class Migration(migrations.Migration):
    # replaces = [
    #     ('activesync', '0001_initial'),
    #     ('activesync', '0004_v1_7__user_settings'),
    # ]
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        # ('auth', '0001_initial'),
        ('creme_core', '0001_initial'),
        ('contenttypes', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='CremeClient',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('client_id', models.CharField(default=creme.activesync.utils.generate_guid, unique=True, max_length=32, verbose_name='Creme Client ID')),
                ('policy_key', models.CharField(default=0, max_length=200, verbose_name='Last policy key')),
                ('sync_key', models.CharField(default=None, max_length=200, null=True, verbose_name='Last sync key', blank=True)),
                ('folder_sync_key', models.CharField(default=None, max_length=200, null=True, verbose_name='Last folder sync key', blank=True)),
                ('contact_folder_id', models.CharField(default=None, max_length=64, null=True, verbose_name='Contact folder id', blank=True)),
                ('last_sync', models.DateTimeField(null=True, verbose_name='Last sync', blank=True)),
                ('user', models.OneToOneField(verbose_name='Assigned to', to=settings.AUTH_USER_MODEL, on_delete=CASCADE)),
            ],
            options={},
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='AS_Folder',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('server_id', models.CharField(max_length=200, verbose_name='Server id')),
                ('parent_id', models.CharField(max_length=200, null=True, verbose_name='Server id', blank=True)),
                ('display_name', models.CharField(default=b'', max_length=200, verbose_name='Display name')),
                ('type', models.IntegerField(verbose_name='Type')),
                ('sync_key', models.CharField(default=None, max_length=200, null=True, verbose_name='sync key', blank=True)),
                ('as_class', models.CharField(default=None, max_length=25, null=True, verbose_name='class', blank=True)),
                ('entity_id', models.CharField(default=None, max_length=200, null=True, verbose_name='Entity id', blank=True)),
                ('client', models.ForeignKey(verbose_name='client', to='activesync.CremeClient', on_delete=CASCADE)),
            ],
            options={},
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='CremeExchangeMapping',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('creme_entity_id', models.IntegerField(unique=True, verbose_name='Creme entity pk')),
                ('exchange_entity_id', models.CharField(unique=True, max_length=64, verbose_name='Exchange entity pk')),
                ('synced', models.BooleanField(default=False, verbose_name='Already synced on server')),
                ('is_creme_modified', models.BooleanField(default=False, verbose_name='Modified by creme?')),
                ('was_deleted', models.BooleanField(default=False, verbose_name='Was deleted by creme?')),
                ('creme_entity_repr', models.CharField(default='', max_length=200, null=True, verbose_name='Verbose entity representation', blank=True)),
                ('creme_entity_ct', creme.creme_core.models.fields.CTypeForeignKey(verbose_name='Creme entity ct', to='contenttypes.ContentType')),
                ('user', models.ForeignKey(verbose_name='Belongs to', to=settings.AUTH_USER_MODEL, on_delete=CASCADE)),
            ],
            options={},
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='EntityASData',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('field_name', models.CharField(max_length=100, verbose_name='Field name')),
                ('field_value', models.CharField(max_length=300, verbose_name='Field value')),
                ('entity', models.ForeignKey(verbose_name='Target entity', to='creme_core.CremeEntity', on_delete=CASCADE)),
            ],
            options={
                'unique_together': {('entity', 'field_name')},
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SyncKeyHistory',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('sync_key', models.CharField(default=None, max_length=200, null=True, verbose_name='sync key', blank=True)),
                ('created', creme.creme_core.models.fields.CreationDateTimeField(default=now, verbose_name='Creation date', editable=False, blank=True)),
                ('client', models.ForeignKey(verbose_name='client', to='activesync.CremeClient', on_delete=CASCADE)),
            ],
            options={},
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='UserSynchronizationHistory',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('entity_repr', models.CharField(default=None, max_length=200, null=True, verbose_name='Entity', blank=True)),
                ('entity_pk', models.IntegerField(null=True, verbose_name='Entity pk', blank=True)),
                ('created', creme.creme_core.models.fields.CreationDateTimeField(default=now, verbose_name='Creation date', editable=False, blank=True)),
                ('entity_changes', models.TextField(default=creme.activesync.models.active_sync._empty_dump, verbose_name='Entity changes')),
                ('type', models.IntegerField(verbose_name='Type', choices=[(1, 'Creation'), (3, 'Update'), (4, 'Deletion')])),
                ('where', models.IntegerField(verbose_name='Where', choices=[(1, 'In Creme'), (2, 'On server')])),
                ('entity_ct', creme.creme_core.models.fields.CTypeForeignKey(verbose_name='What', blank=True, to='contenttypes.ContentType', null=True)),
                ('user', models.ForeignKey(verbose_name='User', to=settings.AUTH_USER_MODEL, on_delete=CASCADE)),
            ],
            options={
                'verbose_name': 'History',
                'verbose_name_plural': 'History',
            },
            bases=(models.Model,),
        ),
    ]
