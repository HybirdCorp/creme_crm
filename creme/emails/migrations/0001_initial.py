# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import models, migrations
from django.db.models.deletion import SET_NULL

import creme.creme_core.models.fields

from creme.documents.models.fields import ImageEntityManyToManyField

import creme.emails.utils


class Migration(migrations.Migration):
    # replaces = [
    #     ('emails', '0001_initial'),
    #     ('emails', '0006_v1_7__charfields_not_null_1'),
    #     ('emails', '0007_v1_7__charfields_not_null_2'),
    #     ('emails', '0008_v1_7__image_to_doc_1'),
    #     ('emails', '0009_v1_7__image_to_doc_2'),
    #     ('emails', '0010_v1_7__image_to_doc_3'),
    #     ('emails', '0011_v1_7__image_to_doc_4'),
    # ]

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('auth', '0001_initial'),
        ('creme_core', '0001_initial'),
        migrations.swappable_dependency(settings.DOCUMENTS_DOCUMENT_MODEL),
        # ('media_managers', '0001_initial'),
        migrations.swappable_dependency(settings.PERSONS_CONTACT_MODEL),
        migrations.swappable_dependency(settings.PERSONS_ORGANISATION_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='EmailSignature',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                ('body', models.TextField(verbose_name='Body')),
                # ('images', models.ManyToManyField(to='media_managers.Image', verbose_name='Images', blank=True)),
                ('images', ImageEntityManyToManyField(help_text='Images embedded in emails (but not as attached).',
                                                      to=settings.DOCUMENTS_DOCUMENT_MODEL,
                                                      verbose_name='Images', blank=True,
                                                     )
                ),
                ('user', models.ForeignKey(verbose_name='User', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('name',),
                'verbose_name': 'Email signature',
                'verbose_name_plural': 'Email signatures',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='MailingList',
            fields=[
                ('cremeentity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='creme_core.CremeEntity')),
                ('name', models.CharField(max_length=80, verbose_name='Name of the mailing list')),
                ('children', models.ManyToManyField(related_name='parents_set', verbose_name='Child mailing lists', to=settings.EMAILS_MLIST_MODEL)),
                ('contacts', models.ManyToManyField(to=settings.PERSONS_CONTACT_MODEL, verbose_name='Contacts recipients')),
                ('organisations', models.ManyToManyField(to=settings.PERSONS_ORGANISATION_MODEL, verbose_name='Organisations recipients')),
            ],
            options={
                'swappable': 'EMAILS_MLIST_MODEL',
                'ordering': ('name',),
                'verbose_name': 'Mailing list',
                'verbose_name_plural': 'Mailing lists',
            },
            bases=('creme_core.cremeentity',),
        ),
        migrations.CreateModel(
            name='EmailCampaign',
            fields=[
                ('cremeentity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='creme_core.CremeEntity')),
                ('name', models.CharField(max_length=100, verbose_name='Name of the campaign')),
                ('mailing_lists', models.ManyToManyField(to=settings.EMAILS_MLIST_MODEL, verbose_name='Related mailing lists', blank=True)),
            ],
            options={
                'swappable': 'EMAILS_CAMPAIGN_MODEL',
                'ordering': ('name',),
                'verbose_name': 'Emailing campaign',
                'verbose_name_plural': 'Emailing campaigns',
            },
            bases=('creme_core.cremeentity',),
        ),
        migrations.CreateModel(
            name='EmailSending',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('sender', models.EmailField(max_length=100, verbose_name='Sender address')),
                ('type', models.PositiveSmallIntegerField(default=1, verbose_name='Sending type', choices=[(1, 'Immediate'), (2, 'Deferred')])),
                ('sending_date', models.DateTimeField(verbose_name='Sending date')),
                ('state', models.PositiveSmallIntegerField(default=3, verbose_name='Sending state', editable=False,
                                                           choices=[(1, 'Done'), (2, 'In progress'), (3, 'Planned'), (4, 'Error during sending')],
                                                          ),
                ),
                ('subject', models.CharField(verbose_name='Subject', max_length=100, editable=False)),
                ('body', models.TextField(verbose_name='Body', editable=False)),
                ('body_html', models.TextField(verbose_name='Body (HTML)', null=True, editable=False)),  # blank=True
                ('attachments', models.ManyToManyField(verbose_name='Attachments', editable=False, to=settings.DOCUMENTS_DOCUMENT_MODEL)),
                ('campaign', models.ForeignKey(related_name='sendings_set', editable=False, to=settings.EMAILS_CAMPAIGN_MODEL, verbose_name='Related campaign')),
                ('signature', models.ForeignKey(on_delete=SET_NULL, editable=False, to='emails.EmailSignature', null=True, verbose_name='Signature')),  # blank=True
            ],
            options={
                'verbose_name': 'Email campaign sending',
                'verbose_name_plural': 'Email campaign sendings',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='EmailTemplate',
            fields=[
                ('cremeentity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='creme_core.CremeEntity')),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                ('subject', models.CharField(max_length=100, verbose_name='Subject')),
                ('body', models.TextField(verbose_name='Body')),
                ('body_html', creme.creme_core.models.fields.UnsafeHTMLField(verbose_name='Body (HTML)')),
                ('attachments', models.ManyToManyField(to=settings.DOCUMENTS_DOCUMENT_MODEL, verbose_name='Attachments')),
                ('signature', models.ForeignKey(on_delete=SET_NULL, verbose_name='Signature', blank=True, to='emails.EmailSignature', null=True)),
            ],
            options={
                'swappable': 'EMAILS_TEMPLATE_MODEL',
                'ordering': ('name',),
                'verbose_name': 'Email template',
                'verbose_name_plural': 'Email templates',
            },
            bases=('creme_core.cremeentity',),
        ),
        migrations.CreateModel(
            name='EntityEmail',
            fields=[
                ('cremeentity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='creme_core.CremeEntity')),
                ('reads', models.PositiveIntegerField(default=0, verbose_name='Number of reads', null=True, editable=False)),  # blank=True
                ('status', models.PositiveSmallIntegerField(default=2, verbose_name='Status', editable=False,
                                                            choices=[(1, 'Sent'), (2, 'Not sent'), (3, 'Sending error'),
                                                                     (4, 'Synchronized'), (5, 'Synchronized - Marked as SPAM'),
                                                                     (6, 'Synchronized - Untreated'),
                                                                    ],
                                                           ),
                ),
                ('sender', models.CharField(max_length=100, verbose_name='Sender')),
                ('recipient', models.CharField(max_length=100, verbose_name='Recipient')),
                ('subject', models.CharField(max_length=100, verbose_name='Subject', blank=True)),
                ('body', models.TextField(verbose_name='Body')),
                ('sending_date', models.DateTimeField(verbose_name='Sending date', null=True, editable=False)),  # blank=True
                ('reception_date', models.DateTimeField(verbose_name='Reception date', null=True, editable=False)),  # blank=True
                ('identifier', models.CharField(default=creme.emails.utils.generate_id, verbose_name='Email ID', unique=True, max_length=32, editable=False)),
                ('body_html', creme.creme_core.models.fields.UnsafeHTMLField(verbose_name='Body (HTML)')),
                ('attachments', models.ManyToManyField(to=settings.DOCUMENTS_DOCUMENT_MODEL, verbose_name='Attachments', blank=True)),
                ('signature', models.ForeignKey(verbose_name='Signature', blank=True, to='emails.EmailSignature', null=True)),
            ],
            options={
                'swappable': 'EMAILS_EMAIL_MODEL',
                'ordering': ('-sending_date',),
                'verbose_name': 'Email',
                'verbose_name_plural': 'Emails',
            },
            bases=('creme_core.cremeentity', models.Model),
        ),
        migrations.CreateModel(
            name='LightWeightEmail',
            fields=[
                ('id', models.CharField(verbose_name='Email ID', max_length=32, serialize=False, editable=False, primary_key=True)),
                ('reads', models.PositiveIntegerField(default=0, verbose_name='Number of reads', null=True, editable=False)),  # blank=True
                ('status', models.PositiveSmallIntegerField(default=2, verbose_name='Status', editable=False,
                                                            choices=[(1, 'Sent'), (2, 'Not sent'), (3, 'Sending error'),
                                                                     (4, 'Synchronized'), (5, 'Synchronized - Marked as SPAM'),
                                                                     (6, 'Synchronized - Untreated'),
                                                                    ],
                                                           ),
                ),
                ('sender', models.CharField(max_length=100, verbose_name='Sender')),
                ('recipient', models.CharField(max_length=100, verbose_name='Recipient')),
                ('subject', models.CharField(max_length=100, verbose_name='Subject', blank=True)),
                ('body', models.TextField(verbose_name='Body')),
                ('sending_date', models.DateTimeField(verbose_name='Sending date', null=True, editable=False)),  # blank=True
                ('reception_date', models.DateTimeField(verbose_name='Reception date', null=True, editable=False)),  # blank=True
                ('recipient_entity', models.ForeignKey(related_name='received_lw_mails', editable=False, to='creme_core.CremeEntity', null=True)),
                ('sending', models.ForeignKey(related_name='mails_set', editable=False, to='emails.EmailSending', verbose_name='Related sending')),
            ],
            options={
                'verbose_name': 'Email of campaign',
                'verbose_name_plural': 'Emails of campaign',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='EmailRecipient',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('address', models.CharField(max_length=100, verbose_name='Email address')),
                ('ml', models.ForeignKey(verbose_name='Related mailing list', to=settings.EMAILS_MLIST_MODEL)),
            ],
            options={
                'ordering': ('address',),
                'verbose_name': 'Recipient',
                'verbose_name_plural': 'Recipients',
            },
            bases=(models.Model,),
        ),
    ]
