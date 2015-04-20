# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('creme_core', '0001_initial'),
        ('persons', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='MessageTemplate',
            fields=[
                ('cremeentity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='creme_core.CremeEntity')),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                ('subject', models.CharField(max_length=100, verbose_name='Subject')),
                ('body', models.TextField(verbose_name='Body')),
            ],
            options={
                'ordering': ('name',),
                'verbose_name': 'Message template',
                'verbose_name_plural': 'Messages templates',
            },
            bases=('creme_core.cremeentity',),
        ),
        migrations.CreateModel(
            name='MessagingList',
            fields=[
                ('cremeentity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='creme_core.CremeEntity')),
                ('name', models.CharField(max_length=80, verbose_name='Name of the messaging list')),
                ('contacts', models.ManyToManyField(to='persons.Contact', verbose_name='Contacts recipients')),
            ],
            options={
                'ordering': ('name',),
                'verbose_name': 'SMS messaging list',
                'verbose_name_plural': 'SMS messaging lists',
            },
            bases=('creme_core.cremeentity',),
        ),
        migrations.CreateModel(
            name='Recipient',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('phone', models.CharField(max_length=100, null=True, verbose_name='Number', blank=True)),
                ('messaging_list', models.ForeignKey(verbose_name='Related messaging list', to='sms.MessagingList')),
            ],
            options={
                'verbose_name': 'Recipient',
                'verbose_name_plural': 'Recipients',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SMSAccount',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=200, null=True, verbose_name='Name')),
                ('credit', models.IntegerField(null=True, verbose_name='Credit')),
                ('groupname', models.CharField(max_length=200, null=True, verbose_name='Group')),
            ],
            options={
                'verbose_name': 'SMS account',
                'verbose_name_plural': 'SMS accounts',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SMSCampaign',
            fields=[
                ('cremeentity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='creme_core.CremeEntity')),
                ('name', models.CharField(max_length=100, verbose_name='Name of the campaign')),
                ('lists', models.ManyToManyField(to='sms.MessagingList', verbose_name='Related messaging lists')),
            ],
            options={
                'ordering': ('name',),
                'verbose_name': 'SMS campaign',
                'verbose_name_plural': 'SMS campaigns',
            },
            bases=('creme_core.cremeentity',),
        ),
        migrations.CreateModel(
            name='Sending',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date', models.DateField(verbose_name='Date')),
                ('content', models.TextField(max_length=160, verbose_name='Generated message')),
                ('campaign', models.ForeignKey(related_name='sendings', verbose_name='Related campaign', to='sms.SMSCampaign')),
                ('template', models.ForeignKey(verbose_name='Message template', to='sms.MessageTemplate')),
            ],
            options={
                'verbose_name': 'Sending',
                'verbose_name_plural': 'Sendings',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('phone', models.CharField(max_length=100, verbose_name='Number')),
                ('status', models.CharField(max_length=10, verbose_name='State')),
                ('status_message', models.CharField(max_length=100, null=True, verbose_name='Full state', blank=True)),
                ('sending', models.ForeignKey(related_name='messages', verbose_name='Sending', to='sms.Sending')),
            ],
            options={
                'verbose_name': 'Message',
                'verbose_name_plural': 'Messages',
            },
            bases=(models.Model,),
        ),
    ]
