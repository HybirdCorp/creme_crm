# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import models, migrations
import django.db.models.deletion

import creme.creme_core.models.fields


class Migration(migrations.Migration):
    dependencies = [
        ('activities', '0001_initial'),
        ('creme_core', '0001_initial'),
        ('persons', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProjectStatus',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                ('color_code', models.CharField(max_length=100, null=True, verbose_name='Color', blank=True)),
                ('description', models.TextField(verbose_name='Description')),
                ('order', creme.creme_core.models.fields.BasicAutoField(verbose_name='Order', editable=False, blank=True)),
            ],
            options={
                'ordering': ('order',),
                'verbose_name': 'Status of project',
                'verbose_name_plural': 'Status of project',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Project',
            fields=[
                ('cremeentity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='creme_core.CremeEntity')),
                ('name', models.CharField(max_length=100, verbose_name='Name of the project')),
                ('description', models.TextField(null=True, verbose_name='Description', blank=True)),
                ('start_date', models.DateTimeField(null=True, verbose_name='Estimated start', blank=True)),
                ('end_date', models.DateTimeField(null=True, verbose_name='Estimated end', blank=True)),
                ('effective_end_date', models.DateTimeField(null=True, verbose_name='Effective end date', blank=True)),
                ('status', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, verbose_name='Status', to='projects.ProjectStatus')),
            ],
            options={
                'ordering': ('name',),
                'verbose_name': 'Project',
                'verbose_name_plural': 'Projects',
            },
            bases=('creme_core.cremeentity',),
        ),
        migrations.CreateModel(
            name='TaskStatus',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                ('color_code', models.CharField(max_length=100, null=True, verbose_name='Color', blank=True)),
                ('description', models.TextField(verbose_name='Description')),
                ('is_custom', models.BooleanField(default=True)),
                ('order', creme.creme_core.models.fields.BasicAutoField(verbose_name='Order', editable=False, blank=True)),
            ],
            options={
                'ordering': ('order',),
                'verbose_name': 'Status of task',
                'verbose_name_plural': 'Statuses of task',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ProjectTask',
            fields=[
                ##('activity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='activities.Activity')),
                #('activity_ptr', models.OneToOneField(parent_link=False, auto_created=True, primary_key=True, serialize=False, to='activities.Activity')),
                ('activity_ptr', models.OneToOneField(parent_link=False, auto_created=True, primary_key=True, serialize=False, to=settings.ACTIVITIES_ACTIVITY_MODEL)),
                ('order', models.PositiveIntegerField(verbose_name='Order', null=True, editable=False, blank=True)),
                ('parent_tasks', models.ManyToManyField(related_name='children_set', null=True, editable=False, to='projects.ProjectTask', blank=True)),
                ('project', models.ForeignKey(related_name='tasks_set', editable=False, to='projects.Project', verbose_name='Project')),
                ('tstatus', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, verbose_name='Task situation', to='projects.TaskStatus')),
            ],
            options={
                'ordering': ('-start',),
                'verbose_name': 'Task of project',
                'verbose_name_plural': 'Tasks of project',
            },
            #bases=('activities.activity',),
            bases=(models.Model,), #TODO: ('creme_core.CremeEntity',) in creme1.7
        ),
        migrations.CreateModel(
            name='Resource',
            fields=[
                ('cremeentity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='creme_core.CremeEntity')),
                ('hourly_cost', models.PositiveIntegerField(null=True, verbose_name='Hourly cost (in \u20ac)', blank=True)),
                #('linked_contact', models.ForeignKey(verbose_name='Contact', to='persons.Contact')),
                ('linked_contact', models.ForeignKey(verbose_name='Contact', to=settings.PERSONS_CONTACT_MODEL)),
                ('task', models.ForeignKey(related_name='resources_set', verbose_name='Task', to='projects.ProjectTask')),
            ],
            options={
                'verbose_name': 'Resource of project',
                'verbose_name_plural': 'Resources of project',
            },
            bases=('creme_core.cremeentity',),
        ),
        migrations.CreateModel(
            name='WorkingPeriod',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('start_date', models.DateTimeField(null=True, verbose_name='Between', blank=True)),
                ('end_date', models.DateTimeField(null=True, verbose_name='And', blank=True)),
                ('duration', models.PositiveIntegerField(null=True, verbose_name='Duration (in hours)', blank=True)),
                ('resource', models.ForeignKey(verbose_name='Resource', to='projects.Resource')),
                ('task', models.ForeignKey(related_name='tasks_set', verbose_name='Task', to='projects.ProjectTask')),
            ],
            options={
                'verbose_name': 'Working period',
                'verbose_name_plural': 'Working periods',
            },
            bases=(models.Model,),
        ),
    ]
