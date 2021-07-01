# -*- coding: utf-8 -*-

from django.conf import settings
from django.db import migrations, models
from django.db.models.deletion import CASCADE, PROTECT
from django.utils.timezone import now

from creme.creme_core.models import fields as creme_fields


class Migration(migrations.Migration):
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
                (
                    'id',
                    models.AutoField(
                        verbose_name='ID', serialize=False, auto_created=True, primary_key=True,
                    )
                ),
                ('title', models.CharField(max_length=200, verbose_name='Title')),
                (
                    'is_ok',
                    models.BooleanField(
                        default=False, editable=False,
                        verbose_name='Expected reaction has been done',
                    )
                ),
                ('description', models.TextField(verbose_name='Source action', blank=True)),
                (
                    'creation_date',
                    creme_fields.CreationDateTimeField(
                        default=now, verbose_name='Creation date', editable=False, blank=True,
                    )
                ),
                ('expected_reaction', models.TextField(verbose_name='Target action', blank=True)),
                ('deadline', models.DateTimeField(verbose_name='Deadline')),
                (
                    'validation_date',
                    models.DateTimeField(
                        verbose_name='Validation date', null=True, editable=False, blank=True,
                    )
                ),
                (
                    'entity',
                    models.ForeignKey(
                        editable=False, on_delete=CASCADE,
                        to='creme_core.CremeEntity', related_name='assistants_actions',
                    )
                ),
                (
                    'entity_content_type',
                    creme_fields.EntityCTypeForeignKey(
                        editable=False, on_delete=CASCADE,
                        related_name='+', to='contenttypes.ContentType',
                    )
                ),
                (
                    'user',
                    creme_fields.CremeUserForeignKey(
                        verbose_name='Owner user', to=settings.AUTH_USER_MODEL,
                    )
                ),
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
                (
                    'id',
                    models.AutoField(
                        verbose_name='ID', serialize=False, auto_created=True, primary_key=True,
                    )
                ),
                ('title', models.CharField(max_length=200, verbose_name='Title')),
                ('description', models.TextField(verbose_name='Description', blank=True)),
                (
                    'is_validated',
                    models.BooleanField(default=False, verbose_name='Validated', editable=False)
                ),
                (
                    'reminded',
                    models.BooleanField(
                        default=False, editable=False, verbose_name='Notification sent',
                    )
                ),
                ('trigger_date', models.DateTimeField(verbose_name='Trigger date')),
                (
                    'entity',
                    models.ForeignKey(
                        editable=False, on_delete=CASCADE,
                        to='creme_core.CremeEntity', related_name='assistants_alerts',
                    )
                ),
                (
                    'entity_content_type',
                    creme_fields.EntityCTypeForeignKey(
                        editable=False, on_delete=CASCADE,
                        related_name='+', to='contenttypes.ContentType',
                    )
                ),
                (
                    'user',
                    creme_fields.CremeUserForeignKey(
                        verbose_name='Owner user', to=settings.AUTH_USER_MODEL,
                    )
                ),
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
                (
                    'id',
                    models.AutoField(
                        verbose_name='ID', serialize=False, auto_created=True, primary_key=True,
                    )
                ),
                ('content', models.TextField(verbose_name='Content')),
                (
                    'on_homepage',
                    models.BooleanField(
                        default=False, verbose_name='Displayed on homepage',  # blank=True,
                    )
                ),
                (
                    'creation_date',
                    creme_fields.CreationDateTimeField(
                        default=now, verbose_name='Creation date', editable=False, blank=True,
                    )
                ),
                (
                    'entity',
                    models.ForeignKey(
                        editable=False, on_delete=CASCADE,
                        to='creme_core.CremeEntity', related_name='assistants_memos',
                    )
                ),
                (
                    'entity_content_type',
                    creme_fields.EntityCTypeForeignKey(
                        editable=False, on_delete=CASCADE,
                        related_name='+', to='contenttypes.ContentType',
                    )
                ),
                (
                    'user',
                    creme_fields.CremeUserForeignKey(
                        verbose_name='Owner user', to=settings.AUTH_USER_MODEL,
                    )
                ),
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
                (
                    'id',
                    models.AutoField(
                        verbose_name='ID', serialize=False, auto_created=True, primary_key=True,
                    )
                ),
                ('title', models.CharField(max_length=200, verbose_name='Title')),
                (
                    'is_ok',
                    models.BooleanField(default=False, verbose_name='Done?', editable=False)
                ),
                (
                    'reminded',
                    models.BooleanField(
                        default=False, editable=False, verbose_name='Notification sent',
                    )
                ),
                ('description', models.TextField(verbose_name='Description', blank=True)),
                (
                    'creation_date',
                    creme_fields.CreationDateTimeField(
                        default=now, verbose_name='Creation date', editable=False, blank=True,
                    )
                ),
                ('deadline', models.DateTimeField(null=True, verbose_name='Deadline', blank=True)),
                (
                    'entity',
                    models.ForeignKey(
                        editable=False, on_delete=CASCADE,
                        to='creme_core.CremeEntity', related_name='assistants_todos',
                    )
                ),
                (
                    'entity_content_type',
                    creme_fields.EntityCTypeForeignKey(
                        editable=False, on_delete=CASCADE,
                        related_name='+', to='contenttypes.ContentType',
                    )
                ),
                (
                    'user',
                    creme_fields.CremeUserForeignKey(
                        verbose_name='Owner user', to=settings.AUTH_USER_MODEL,
                    )
                ),
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
                (
                    'id',
                    models.AutoField(
                        verbose_name='ID', serialize=False, auto_created=True, primary_key=True,
                    )
                ),
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
                (
                    'id',
                    models.AutoField(
                        verbose_name='ID', serialize=False, auto_created=True, primary_key=True,
                    )
                ),
                ('title', models.CharField(max_length=200, verbose_name='Title')),
                ('body', models.TextField(verbose_name='Message body')),
                ('creation_date', models.DateTimeField(verbose_name='Creation date')),
                ('email_sent', models.BooleanField(default=False)),
                (
                    'entity',
                    models.ForeignKey(
                        editable=False, on_delete=CASCADE, null=True,
                        to='creme_core.CremeEntity', related_name='assistants_messages',
                    )
                ),
                (
                    'entity_content_type',
                    creme_fields.EntityCTypeForeignKey(
                        editable=False, on_delete=CASCADE, null=True,
                        related_name='+', to='contenttypes.ContentType',
                    )
                ),
                (
                    'priority',
                    models.ForeignKey(
                        on_delete=PROTECT, verbose_name='Priority',
                        to='assistants.UserMessagePriority',
                    )
                ),
                (
                    'recipient',
                    creme_fields.CremeUserForeignKey(
                        to=settings.AUTH_USER_MODEL, verbose_name='Recipient',
                        related_name='received_assistants_messages_set',
                    )
                ),
                (
                    'sender',
                    creme_fields.CremeUserForeignKey(
                        to=settings.AUTH_USER_MODEL, verbose_name='Sender',
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
