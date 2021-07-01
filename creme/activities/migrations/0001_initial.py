# -*- coding: utf-8 -*-

from django.conf import settings
from django.db import migrations, models
from django.db.models.deletion import CASCADE, PROTECT, SET_NULL

from creme.creme_core.models import CREME_REPLACE_NULL
from creme.creme_core.models import fields as creme_fields


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ('auth', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('creme_core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ActivityType',
            fields=[
                (
                    'id',
                    models.CharField(
                        max_length=100, serialize=False, editable=False, primary_key=True,
                    )
                ),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                ('default_day_duration', models.IntegerField(verbose_name='Default day duration')),
                (
                    'default_hour_duration',
                    creme_fields.DurationField(max_length=15, verbose_name='Default hour duration')
                ),
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
                (
                    'id',
                    models.CharField(
                        max_length=100, serialize=False, editable=False, primary_key=True,
                    )
                ),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                ('is_custom', models.BooleanField(default=True, editable=False)),
                (
                    'type',
                    models.ForeignKey(
                        verbose_name='Type of activity', to='activities.ActivityType',
                        on_delete=CASCADE,
                    )
                ),
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
                (
                    'id',
                    models.AutoField(
                        verbose_name='ID', serialize=False, auto_created=True, primary_key=True,
                    )
                ),
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
                (
                    'id',
                    models.AutoField(
                        verbose_name='ID', serialize=False, auto_created=True, primary_key=True,
                    )
                ),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                ('is_default', models.BooleanField(default=False, verbose_name='Is default?')),
                ('is_custom', models.BooleanField(default=True, editable=False)),
                ('is_public', models.BooleanField(default=False, verbose_name='Is public?')),
                ('color', creme_fields.ColorField(max_length=6, verbose_name='Color')),
                (
                    'user',
                    creme_fields.CremeUserForeignKey(
                        verbose_name='Calendar owner', to=settings.AUTH_USER_MODEL,
                    )
                ),
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
                (
                    'cremeentity_ptr',
                    models.OneToOneField(
                        parent_link=True, auto_created=True, primary_key=True, serialize=False,
                        to='creme_core.CremeEntity', on_delete=CASCADE,
                    ),
                ),
                ('title', models.CharField(max_length=100, verbose_name='Title')),
                ('start', models.DateTimeField(null=True, verbose_name='Start', blank=True)),
                ('end', models.DateTimeField(null=True, verbose_name='End', blank=True)),
                ('minutes', models.TextField(verbose_name='Minutes', blank=True)),
                (
                    'place',
                    models.CharField(max_length=500, verbose_name='Activity place', blank=True)
                ),
                (
                    'duration',
                    models.PositiveIntegerField(
                        verbose_name='Duration (in hour)', blank=True, null=True,
                        help_text='It is only informative and is not used '
                                  'to compute the end time.',
                    ),
                ),
                (
                    'is_all_day',
                    models.BooleanField(default=False, verbose_name='All day?')  # blank=True
                ),
                ('busy', models.BooleanField(default=False, verbose_name='Busy?')),
                (
                    'floating_type',
                    models.PositiveIntegerField(
                        default=1, verbose_name='Floating type', editable=False,
                    )
                ),
                (
                    'type',
                    models.ForeignKey(
                        on_delete=PROTECT, verbose_name='Activity type',
                        to='activities.ActivityType',
                    )
                ),
                (
                    'sub_type',
                    models.ForeignKey(
                        verbose_name='Activity sub-type', to='activities.ActivitySubType',
                        blank=True, null=True, on_delete=SET_NULL,
                    ),
                ),
                (
                    'status',
                    models.ForeignKey(
                        on_delete=CREME_REPLACE_NULL, verbose_name='Status',
                        blank=True, to='activities.Status', null=True,
                    ),
                ),
                (
                    'calendars',
                    models.ManyToManyField(
                        verbose_name='Calendars', editable=False, to='activities.Calendar',
                    )
                ),
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
