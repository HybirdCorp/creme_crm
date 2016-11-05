# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import models, migrations
import django.db.models.deletion

import creme.creme_core.models.fields

import creme.emails.utils


class Migration(migrations.Migration):
    dependencies = [
        #migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('auth', '0001_initial'),
        ('creme_core', '0001_initial'),
        #('documents', '0001_initial'),
        migrations.swappable_dependency(settings.DOCUMENTS_DOCUMENT_MODEL),
        ('media_managers', '0001_initial'),
        #('persons', '0001_initial'),
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
                ('images', models.ManyToManyField(to='media_managers.Image', verbose_name='Images', blank=True)), # null=True
                #('user', models.ForeignKey(verbose_name='User', to=settings.AUTH_USER_MODEL)),
                ('user', models.ForeignKey(verbose_name='User', to='auth.User')),
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
                #('children', models.ManyToManyField(related_name='parents_set', verbose_name='Child mailing lists', to='emails.MailingList')),
                ('children', models.ManyToManyField(related_name='parents_set', verbose_name='Child mailing lists', to=settings.EMAILS_MLIST_MODEL)),
                #('contacts', models.ManyToManyField(to='persons.Contact', verbose_name='Contacts recipients')),
                ('contacts', models.ManyToManyField(to=settings.PERSONS_CONTACT_MODEL, verbose_name='Contacts recipients')),
                #('organisations', models.ManyToManyField(to='persons.Organisation', verbose_name='Organisations recipients')),
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
                #('mailing_lists', models.ManyToManyField(to='emails.MailingList', verbose_name='Related mailing lists')),
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
                ('type', models.PositiveSmallIntegerField(verbose_name='Sending type')),
                ('sending_date', models.DateTimeField(verbose_name='Sending date of emails')),
                ('state', models.PositiveSmallIntegerField(verbose_name='Sending state', editable=False)),
                ('subject', models.CharField(verbose_name='Subject', max_length=100, editable=False)),
                ('body', models.TextField(verbose_name='Body', editable=False)),
                ('body_html', models.TextField(verbose_name='Body (HTML)', null=True, editable=False, blank=True)),
                #('attachments', models.ManyToManyField(verbose_name='Attachments', editable=False, to='documents.Document')),
                ('attachments', models.ManyToManyField(verbose_name='Attachments', editable=False, to=settings.DOCUMENTS_DOCUMENT_MODEL)),
                #('campaign', models.ForeignKey(related_name='sendings_set', editable=False, to='emails.EmailCampaign', verbose_name='Related campaign')),
                ('campaign', models.ForeignKey(related_name='sendings_set', editable=False, to=settings.EMAILS_CAMPAIGN_MODEL, verbose_name='Related campaign')),
                ('signature', models.ForeignKey(blank=True, editable=False, to='emails.EmailSignature', null=True, verbose_name='Signature')),
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
                # ('body_html', models.TextField(verbose_name='Body (HTML)')),
                ('body_html', creme.creme_core.models.fields.UnsafeHTMLField(verbose_name='Body (HTML)')),
                #('attachments', models.ManyToManyField(to='documents.Document', verbose_name='Attachments')),
                ('attachments', models.ManyToManyField(to=settings.DOCUMENTS_DOCUMENT_MODEL, verbose_name='Attachments')),
                ('signature', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, verbose_name='Signature', blank=True, to='emails.EmailSignature', null=True)),
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
                ('reads', models.PositiveIntegerField(default=0, null=True, verbose_name='Number of reads', blank=True)),
                ('status', models.PositiveSmallIntegerField(default=2, verbose_name='Status')),
                ('sender', models.CharField(max_length=100, verbose_name='Sender')),
                ('recipient', models.CharField(max_length=100, verbose_name='Recipient')),
                ('subject', models.CharField(max_length=100, null=True, verbose_name='Subject', blank=True)),
                ('body', models.TextField(verbose_name='Body')),
                ('sending_date', models.DateTimeField(null=True, verbose_name='Sending date', blank=True)),
                ('reception_date', models.DateTimeField(null=True, verbose_name='Reception date', blank=True)),
                ('identifier', models.CharField(default=creme.emails.utils.generate_id, verbose_name='Email ID', unique=True, max_length=32, editable=False)),
                # ('body_html', models.TextField(verbose_name='Body (HTML)')),
                ('body_html', creme.creme_core.models.fields.UnsafeHTMLField(verbose_name='Body (HTML)')),
                #('attachments', models.ManyToManyField(to='documents.Document', verbose_name='Attachments')),
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
                ('reads', models.PositiveIntegerField(default=0, null=True, verbose_name='Number of reads', blank=True)),
                ('status', models.PositiveSmallIntegerField(default=2, verbose_name='Status')),
                ('sender', models.CharField(max_length=100, verbose_name='Sender')),
                ('recipient', models.CharField(max_length=100, verbose_name='Recipient')),
                ('subject', models.CharField(max_length=100, null=True, verbose_name='Subject', blank=True)),
                ('body', models.TextField(verbose_name='Body')),
                ('sending_date', models.DateTimeField(null=True, verbose_name='Sending date', blank=True)),
                ('reception_date', models.DateTimeField(null=True, verbose_name='Reception date', blank=True)),
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
                ('address', models.CharField(max_length=100, null=True, verbose_name='Email address', blank=True)),
                #('ml', models.ForeignKey(verbose_name='Related mailing list', to='emails.MailingList')),
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
