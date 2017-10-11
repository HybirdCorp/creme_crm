# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import models, migrations
from django.db.models import deletion

import creme.creme_core.models.fields


class Migration(migrations.Migration):
    # replaces = [
    #     (b'activities', '0001_initial'),
    #     (b'activities', '0002_v1_6__convert_user_FKs'),
    #     (b'activities', '0003_v1_6__fk_on_delete_set'),
    #     (b'activities', '0004_v_1_6__django18_hints'),
    #     (b'activities', '0005_v1_6__field_place_is_longer'),
    # ]

    dependencies = [
        ('auth', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('creme_core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ActivityType',
            fields=[
                ('id', models.CharField(max_length=100, serialize=False, editable=False, primary_key=True)),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                ('default_day_duration', models.IntegerField(verbose_name='Default day duration')),
                ('default_hour_duration', creme.creme_core.models.fields.DurationField(max_length=15, verbose_name='Default hour duration')),
                ('is_custom', models.BooleanField(default=True, editable=False)),
            ],
            options={
                'ordering': ('name',),
                'verbose_name': 'Type of activity',
                'verbose_name_plural': 'Types of activity',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ActivitySubType',
            fields=[
                ('id', models.CharField(max_length=100, serialize=False, editable=False, primary_key=True)),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                ('is_custom', models.BooleanField(default=True, editable=False)),
                ('type', models.ForeignKey(verbose_name='Type of activity', to='activities.ActivityType')),
            ],
            options={
                'ordering': ('name',),
                'verbose_name': 'Sub-type of activity',
                'verbose_name_plural': 'Sub-types of activity',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Status',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                ('description', models.TextField(verbose_name='Description')),
                ('is_custom', models.BooleanField(default=True)),
            ],
            options={
                'ordering': ('name',),
                'verbose_name': 'Status of activity',
                'verbose_name_plural': 'Status of activity',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Calendar',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                ('is_default', models.BooleanField(default=False, verbose_name='Is default?')),
                ('is_custom', models.BooleanField(default=True, editable=False)),
                ('is_public', models.BooleanField(default=False, verbose_name='Is public?')),
                ('color', models.CharField(max_length=100, null=True, verbose_name='Color', blank=True)),
                ('user', creme.creme_core.models.fields.CremeUserForeignKey(verbose_name='Calendar owner', to=settings.AUTH_USER_MODEL)),
                # ('user', creme.creme_core.models.fields.CremeUserForeignKey(verbose_name='Calendar owner', to='auth.User')),
            ],
            options={
                'ordering': ['name'],
                'verbose_name': 'Calendar',
                'verbose_name_plural': 'Calendars',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Activity',
            fields=[
                ('cremeentity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='creme_core.CremeEntity')),
                ('title', models.CharField(max_length=100, verbose_name='Title')),
                ('start', models.DateTimeField(null=True, verbose_name='Start', blank=True)),
                ('end', models.DateTimeField(null=True, verbose_name='End', blank=True)),
                ('description', models.TextField(null=True, verbose_name='Description', blank=True)),
                ('minutes', models.TextField(null=True, verbose_name='Minutes', blank=True)),
                # ('place', models.CharField(max_length=100, null=True, verbose_name='Activity place', blank=True)),
                ('place', models.CharField(max_length=500, null=True, verbose_name='Activity place', blank=True)),
                ('duration', models.PositiveIntegerField(null=True, verbose_name='Duration (in hour)', blank=True)),
                ('is_all_day', models.BooleanField(default=False, verbose_name='All day?')),
                ('busy', models.BooleanField(default=False, verbose_name='Busy?')),
                ('floating_type', models.PositiveIntegerField(default=1, verbose_name='Floating type', editable=False)),
                ('type', models.ForeignKey(on_delete=deletion.PROTECT, verbose_name='Activity type', to='activities.ActivityType')),
                ('sub_type',models.ForeignKey(on_delete=deletion.SET_NULL, verbose_name='Activity sub-type', blank=True, to='activities.ActivitySubType', null=True)),
                # ('status', models.ForeignKey(verbose_name='Status', blank=True, to='activities.Status', null=True)),
                ('status', models.ForeignKey(on_delete=deletion.SET_NULL, verbose_name='Status', blank=True, to='activities.Status', null=True)),
                # ('calendars', models.ManyToManyField(verbose_name='Calendars', editable=False, to='activities.Calendar')),
                ('calendars', models.ManyToManyField(verbose_name='Calendars', editable=False, to='activities.Calendar', blank=True)),
            ],
            options={
                'swappable': 'ACTIVITIES_ACTIVITY_MODEL',
                'ordering': ('-start',),
                'verbose_name': 'Activity',
                'verbose_name_plural': 'Activities',
            },
            bases=('creme_core.cremeentity',),
        ),
    ]
