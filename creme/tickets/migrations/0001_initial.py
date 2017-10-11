# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion

import creme.creme_core.models.fields


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Criticity',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=100, verbose_name='Name')),
                ('order', creme.creme_core.models.fields.BasicAutoField(verbose_name='Order', editable=False, blank=True)),
            ],
            options={
                'ordering': ('order',),
                'verbose_name': 'Ticket criticality',
                'verbose_name_plural': 'Ticket criticalities',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Priority',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=100, verbose_name='Name')),
                ('order', creme.creme_core.models.fields.BasicAutoField(verbose_name='Order', editable=False, blank=True)),
            ],
            options={
                'ordering': ('order',),
                'verbose_name': 'Ticket priority',
                'verbose_name_plural': 'Ticket priorities',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Status',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=100, verbose_name='Name')),
                ('is_custom', models.BooleanField(default=True)),
                ('order', creme.creme_core.models.fields.BasicAutoField(verbose_name='Order', editable=False, blank=True)),
            ],
            options={
                'ordering': ('order',),
                'verbose_name': 'Ticket status',
                'verbose_name_plural': 'Ticket statuses',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
                name='TicketNumber',
                fields=[
                    ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ],
        ),
        migrations.CreateModel(
            name='Ticket',
            fields=[
                ('cremeentity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='creme_core.CremeEntity')),
                ('number', models.PositiveIntegerField(verbose_name='Number', unique=True, editable=False)),
                # ('title', models.CharField(unique=True, max_length=100, verbose_name='Title', blank=True)),
                ('title', models.CharField(max_length=100, verbose_name='Title', blank=True)),
                ('description', models.TextField(verbose_name='Description')),
                ('solution', models.TextField(verbose_name='Solution', blank=True)),
                ('closing_date', models.DateTimeField(verbose_name='Closing date', null=True, editable=False, blank=True)),
                ('criticity', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, verbose_name='Criticity', to='tickets.Criticity')),
                ('priority', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, verbose_name='Priority', to='tickets.Priority')),
                ('status', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, verbose_name='Status', to='tickets.Status')),
            ],
            options={
                'swappable': 'TICKETS_TICKET_MODEL',
                'ordering': ('title',),
                'verbose_name': 'Ticket',
                'verbose_name_plural': 'Tickets',
            },
            bases=('creme_core.cremeentity',),
        ),
        migrations.CreateModel(
            name='TicketTemplate',
            fields=[
                ('cremeentity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='creme_core.CremeEntity')),
                # ('title', models.CharField(unique=True, max_length=100, verbose_name='Title', blank=True)),
                ('title', models.CharField(max_length=100, verbose_name='Title', blank=True)),
                ('description', models.TextField(verbose_name='Description')),
                ('solution', models.TextField(verbose_name='Solution', blank=True)),
                ('criticity', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, verbose_name='Criticity', to='tickets.Criticity')),
                ('priority', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, verbose_name='Priority', to='tickets.Priority')),
                ('status', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, verbose_name='Status', to='tickets.Status')),
            ],
            options={
                'swappable': 'TICKETS_TEMPLATE_MODEL',
                'ordering': ('title',),
                'verbose_name': 'Ticket template',
                'verbose_name_plural': 'Ticket templates',
            },
            bases=('creme_core.cremeentity',),
        ),
    ]
