import datetime
from uuid import uuid4

from django.conf import settings
from django.db import migrations, models
from django.db.models.deletion import CASCADE, PROTECT

import creme.creme_core.models.fields as creme_fields
from creme.activities.models.config import Weekday
from creme.creme_core.models import CREME_REPLACE_NULL


class Migration(migrations.Migration):
    # replaces = [
    #     ('activities', '0001_initial'),
    #     ('activities', '0029_v2_7__floating_type_choices'),
    #     ('activities', '0030_v2_7__calendarconfigitem_view_day'),
    # ]
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
                    models.AutoField(
                        verbose_name='ID', serialize=False, auto_created=True, primary_key=True,
                    )
                ),
                ('uuid', models.UUIDField(default=uuid4, editable=False, unique=True)),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                (
                    'default_day_duration',
                    models.IntegerField(verbose_name='Default day duration', default=0)
                ),
                (
                    'default_hour_duration',
                    creme_fields.DurationField(max_length=15, verbose_name='Default hour duration')
                ),
                ('is_custom', models.BooleanField(default=True, editable=False)),
                ('extra_data', models.JSONField(default=dict, editable=False)),
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
                    models.AutoField(
                        verbose_name='ID', serialize=False, auto_created=True, primary_key=True,
                    )
                ),
                ('uuid', models.UUIDField(default=uuid4, editable=False, unique=True)),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                ('is_custom', models.BooleanField(default=True, editable=False)),
                (
                    'type',
                    models.ForeignKey(
                        verbose_name='Type of activity', to='activities.ActivityType',
                        on_delete=CASCADE,
                    )
                ),
                ('extra_data', models.JSONField(default=dict, editable=False)),
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
                (
                    'color',
                    creme_fields.ColorField(
                        default=creme_fields.ColorField.random,
                        max_length=6, verbose_name='Color',
                    )
                ),
                ('is_custom', models.BooleanField(default=True, editable=False)),
                ('extra_data', models.JSONField(default=dict, editable=False)),
                ('uuid', models.UUIDField(default=uuid4, editable=False, unique=True)),
            ],
            options={
                'ordering': ('name',),
                'verbose_name': 'Status of activity',
                'verbose_name_plural': 'Status of activity',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='CalendarConfigItem',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    )
                ),
                ('superuser', models.BooleanField(default=False, editable=False)),
                (
                    'view',
                    models.CharField(
                        verbose_name='Default view mode',
                        choices=[('month', 'Month'), ('week', 'Week')], default='month',
                        max_length=100,
                    )
                ),
                (
                    'week_start',
                    models.IntegerField(
                        verbose_name='First day of the week',
                        choices=[
                            (1, 'Monday'), (2, 'Tuesday'), (3, 'Wednesday'), (4, 'Thursday'),
                            (5, 'Friday'), (6, 'Saturday'), (7, 'Sunday'),
                        ],
                        default=1,
                    )
                ),
                (
                    'week_days',
                    models.JSONField(
                        verbose_name='Days of the week',
                        default=Weekday.default_days, editable=False,
                    )
                ),
                ('day_start', models.TimeField(default=datetime.time(8, 0), verbose_name='Start')),
                ('day_end', models.TimeField(default=datetime.time(18, 0), verbose_name='End')),
                (
                    'slot_duration',
                    models.TimeField(default=datetime.time(0, 15), verbose_name='Slot duration')
                ),
                (
                    'allow_event_move',
                    models.BooleanField(default=True, verbose_name='Allow drag-n-drop')
                ),
                (
                    'allow_keep_state',
                    models.BooleanField(default=False, verbose_name='Keep navigation state')
                ),
                (
                    'view_day_end',
                    models.TimeField(
                        verbose_name='View end', default=datetime.time(0, 0),
                        help_text=(
                            'End of the displayed hours.\n'
                            'Can be different from the day range that restricts the moves and creation of events'
                        ),
                    ),
                ),
                (
                    'view_day_start',
                    models.TimeField(
                        verbose_name='View start', default=datetime.time(0, 0),
                        help_text=(
                            'Start of the displayed hours.\n'
                            'Can be different from the day range that restricts the moves and creation of events'
                        ),
                    ),
                ),
                ('extra_data', models.JSONField(default=dict, editable=False)),
                (
                    'role',
                    models.ForeignKey(
                        to='creme_core.userrole',
                        default=None, editable=False, null=True, on_delete=CASCADE,
                    )
                ),
            ],
            options={
                'verbose_name': 'Calendar display configuration',
                'verbose_name_plural': 'Calendar display configurations',
            },
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
                (
                    'is_default',
                    models.BooleanField(
                        default=False, verbose_name='Is default?',
                        help_text=(
                            "When a user is set as an Activity's participant, "
                            "this Activity is added to its default calendar."
                        ),
                    )
                ),
                ('is_custom', models.BooleanField(default=True, editable=False)),
                (
                    'is_public',
                    models.BooleanField(
                        default=False, verbose_name='Is public?',
                        help_text='Public calendars can be seen by other users on the calendar view.',
                    )
                ),
                (
                    'color',
                    creme_fields.ColorField(
                        max_length=6, verbose_name='Color',
                        help_text='It is used on the calendar view to colorize Activities.',
                        default=creme_fields.ColorField.random,
                    )
                ),
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
                    models.BooleanField(default=False, verbose_name='All day?')
                ),
                ('busy', models.BooleanField(default=False, verbose_name='Busy?')),
                (
                    'floating_type',
                    models.PositiveSmallIntegerField(
                        choices=[(1, 'Fixed'), (2, 'Floating time'), (3, 'Floating')],
                        default=1, editable=False, verbose_name='Fixed or floating?',
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
                        to='activities.activitysubtype',
                        verbose_name='Activity sub-type',
                        on_delete=PROTECT,
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
