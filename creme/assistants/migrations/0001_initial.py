# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import models, migrations
from django.db.models.deletion import PROTECT, CASCADE
from django.utils.timezone import now

from creme.creme_core.models import fields as creme_fields


class Migration(migrations.Migration):
    # replaces = [
    #     (b'assistants', '0001_initial'),
    #     (b'assistants', '0003_v1_7__textfields_not_null_1'),
    #     (b'assistants', '0004_v1_7__textfields_not_null_2'),
    #     (b'assistants', '0005_v1_7__image_to_doc'),
    # ]

    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
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
                ('description', models.TextField(verbose_name='Source action', blank=True)),
                ('creation_date', creme_fields.CreationDateTimeField(default=now, verbose_name='Creation date', editable=False, blank=True)),
                ('expected_reaction', models.TextField(verbose_name='Target action', blank=True)),
                ('deadline', models.DateTimeField(verbose_name='Deadline')),
                ('validation_date', models.DateTimeField(verbose_name='Validation date', null=True, editable=False, blank=True)),
                ('entity_id', models.PositiveIntegerField(editable=False)),
                ('entity_content_type', models.ForeignKey(related_name='action_entity_set', editable=False, to='contenttypes.ContentType', on_delete=CASCADE)),
                ('user', creme_fields.CremeUserForeignKey(verbose_name='Owner user', to=settings.AUTH_USER_MODEL)),
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
                ('description', models.TextField(verbose_name='Description', blank=True)),
                ('is_validated', models.BooleanField(default=False, verbose_name='Validated', editable=False)),
                ('reminded', models.BooleanField(default=False, editable=False, verbose_name=u'Notification sent')),
                ('trigger_date', models.DateTimeField(verbose_name='Trigger date')),
                ('entity_id', models.PositiveIntegerField(editable=False)),
                ('entity_content_type', models.ForeignKey(related_name='alert_entity_set', editable=False, to='contenttypes.ContentType', on_delete=CASCADE)),
                ('user', creme_fields.CremeUserForeignKey(verbose_name='Owner user', to=settings.AUTH_USER_MODEL)),
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
                ('content', models.TextField(verbose_name='Content')),
                ('on_homepage', models.BooleanField(default=False, verbose_name='Displayed on homepage')),
                ('creation_date', creme_fields.CreationDateTimeField(default=now, verbose_name='Creation date', editable=False, blank=True)),
                ('entity_id', models.PositiveIntegerField(editable=False)),
                ('entity_content_type', models.ForeignKey(related_name='memo_entity_set', editable=False, to='contenttypes.ContentType', on_delete=CASCADE)),
                ('user', creme_fields.CremeUserForeignKey(verbose_name='Owner user', to=settings.AUTH_USER_MODEL)),
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
                ('description', models.TextField(verbose_name='Description', blank=True)),
                ('creation_date', creme_fields.CreationDateTimeField(default=now, verbose_name='Creation date', editable=False, blank=True)),
                ('deadline', models.DateTimeField(null=True, verbose_name='Deadline', blank=True)),
                ('entity_id', models.PositiveIntegerField(editable=False)),
                ('entity_content_type', models.ForeignKey(related_name='todo_entity_set', editable=False, to='contenttypes.ContentType', on_delete=CASCADE)),
                ('user', creme_fields.CremeUserForeignKey(verbose_name='Owner user', to=settings.AUTH_USER_MODEL)),
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
                ('entity_content_type', models.ForeignKey(to='contenttypes.ContentType', null=True, on_delete=CASCADE)),
                ('priority', models.ForeignKey(on_delete=PROTECT, verbose_name='Priority', to='assistants.UserMessagePriority')),
                ('recipient', creme_fields.CremeUserForeignKey(to=settings.AUTH_USER_MODEL, verbose_name='Recipient',
                                                               related_name='received_assistants_messages_set',
                                                              )
                ),
                ('sender', creme_fields.CremeUserForeignKey(to=settings.AUTH_USER_MODEL, verbose_name='Sender',
                                                            related_name='sent_assistants_messages_set',
                                                           )
                ),
            ],
            options={
                'verbose_name': 'User message',
                'verbose_name_plural': 'User messages',
            },
            bases=(models.Model,),
        ),
    ]
