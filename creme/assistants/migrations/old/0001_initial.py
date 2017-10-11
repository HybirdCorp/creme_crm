# -*- coding: utf-8 -*-
from __future__ import unicode_literals

#from django.conf import settings
from django.db import models, migrations
import django.db.models.deletion
import django.utils.timezone

import creme.creme_core.models.fields


class Migration(migrations.Migration):
    dependencies = [
        #migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('auth', '0001_initial'),
        ('contenttypes', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Action',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=200, verbose_name='Title')),
                ('is_ok', models.BooleanField(default=False, verbose_name='Expected reaction has been done', editable=False)),
                ('description', models.TextField(null=True, verbose_name='Source action', blank=True)),
                ('creation_date', creme.creme_core.models.fields.CreationDateTimeField(default=django.utils.timezone.now, verbose_name='Creation date', editable=False, blank=True)),
                ('expected_reaction', models.TextField(null=True, verbose_name='Target action', blank=True)),
                ('deadline', models.DateTimeField(verbose_name='Deadline')),
                ('validation_date', models.DateTimeField(verbose_name='Validation date', null=True, editable=False, blank=True)),
                ('entity_id', models.PositiveIntegerField(editable=False)),
                ('entity_content_type', models.ForeignKey(related_name='action_entity_set', editable=False, to='contenttypes.ContentType')),
                #('user', creme.creme_core.models.fields.CremeUserForeignKey(verbose_name='Owner user', to=settings.AUTH_USER_MODEL)),
                ('user', creme.creme_core.models.fields.CremeUserForeignKey(verbose_name='Owner user', to='auth.User')),
            ],
            options={
                'verbose_name': 'Action',
                'verbose_name_plural': 'Actions',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Alert',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=200, verbose_name='Title')),
                ('description', models.TextField(null=True, verbose_name='Description', blank=True)),
                ('is_validated', models.BooleanField(default=False, verbose_name='Validated', editable=False)),
                ('reminded', models.BooleanField(default=False, editable=False, verbose_name=u'Notification sent')),
                ('trigger_date', models.DateTimeField(verbose_name='Trigger date')),
                ('entity_id', models.PositiveIntegerField(editable=False)),
                ('entity_content_type', models.ForeignKey(related_name='alert_entity_set', editable=False, to='contenttypes.ContentType')),
                #('user', creme.creme_core.models.fields.CremeUserForeignKey(verbose_name='Owner user', to=settings.AUTH_USER_MODEL)),
                ('user', creme.creme_core.models.fields.CremeUserForeignKey(verbose_name='Owner user', to='auth.User')),
            ],
            options={
                'verbose_name': 'Alert',
                'verbose_name_plural': 'Alerts',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Memo',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('content', models.TextField(null=True, verbose_name='Content', blank=True)),
                ('on_homepage', models.BooleanField(default=False, verbose_name='Displayed on homepage')),
                ('creation_date', creme.creme_core.models.fields.CreationDateTimeField(default=django.utils.timezone.now, verbose_name='Creation date', editable=False, blank=True)),
                ('entity_id', models.PositiveIntegerField(editable=False)),
                ('entity_content_type', models.ForeignKey(related_name='memo_entity_set', editable=False, to='contenttypes.ContentType')),
                #('user', creme.creme_core.models.fields.CremeUserForeignKey(verbose_name='Owner user', to=settings.AUTH_USER_MODEL)),
                ('user', creme.creme_core.models.fields.CremeUserForeignKey(verbose_name='Owner user', to='auth.User')),
            ],
            options={
                'verbose_name': 'Memo',
                'verbose_name_plural': 'Memos',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ToDo',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=200, verbose_name='Title')),
                ('is_ok', models.BooleanField(default=False, verbose_name='Done ?', editable=False)),
                ('reminded', models.BooleanField(default=False, editable=False, verbose_name=u'Notification sent')),
                ('description', models.TextField(null=True, verbose_name='Description', blank=True)),
                ('creation_date', creme.creme_core.models.fields.CreationDateTimeField(default=django.utils.timezone.now, verbose_name='Creation date', editable=False, blank=True)),
                ('deadline', models.DateTimeField(null=True, verbose_name='Deadline', blank=True)),
                ('entity_id', models.PositiveIntegerField(editable=False)),
                ('entity_content_type', models.ForeignKey(related_name='todo_entity_set', editable=False, to='contenttypes.ContentType')),
                #('user', creme.creme_core.models.fields.CremeUserForeignKey(verbose_name='Owner user', to=settings.AUTH_USER_MODEL)),
                ('user', creme.creme_core.models.fields.CremeUserForeignKey(verbose_name='Owner user', to='auth.User')),
            ],
            options={
                'verbose_name': 'Todo',
                'verbose_name_plural': 'Todos',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='UserMessagePriority',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=200, verbose_name='Title')),
                ('is_custom', models.BooleanField(default=True)),
            ],
            options={
                'ordering': ('title',),
                'verbose_name': 'Priority of user message',
                'verbose_name_plural': 'Priorities of user message',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='UserMessage',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=200, verbose_name='Title')),
                ('body', models.TextField(verbose_name='Message body')),
                ('creation_date', models.DateTimeField(verbose_name='Creation date')),
                ('email_sent', models.BooleanField(default=False)),
                ('entity_id', models.PositiveIntegerField(null=True)),
                ('entity_content_type', models.ForeignKey(to='contenttypes.ContentType', null=True)),
                ('priority', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, verbose_name='Priority', to='assistants.UserMessagePriority')),
                #('recipient', creme.creme_core.models.fields.CremeUserForeignKey(related_name='received_assistants_messages_set', verbose_name='Recipient', to=settings.AUTH_USER_MODEL)),
                ('recipient', creme.creme_core.models.fields.CremeUserForeignKey(related_name='received_assistants_messages_set', verbose_name='Recipient', to='auth.User')),
                #('sender', creme.creme_core.models.fields.CremeUserForeignKey(related_name='sent_assistants_messages_set', verbose_name='Sender', to=settings.AUTH_USER_MODEL)),
                ('sender', creme.creme_core.models.fields.CremeUserForeignKey(related_name='sent_assistants_messages_set', verbose_name='Sender', to='auth.User')),
            ],
            options={
                'verbose_name': 'User message',
                'verbose_name_plural': 'User messages',
            },
            bases=(models.Model,),
        ),
    ]
