import uuid

from django.conf import settings
from django.db import migrations, models
from django.db.models.deletion import CASCADE, PROTECT

import creme.creme_core.models.fields as creme_fields
from creme.creme_core.models import CREME_REPLACE_NULL


class Migration(migrations.Migration):
    # replaces = [
    #     ('activities', '0001_initial'),
    #     ('activities', '0020_v2_5__status_color01'),
    #     ('activities', '0021_v2_5__status_color02'),
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
                    models.CharField(
                        max_length=100, serialize=False, editable=False, primary_key=True,
                    )
                ),
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
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
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
