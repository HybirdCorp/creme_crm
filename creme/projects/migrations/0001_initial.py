from uuid import uuid4

from django.conf import settings
from django.db import migrations, models
from django.db.models.deletion import CASCADE, PROTECT

import creme.creme_core.models.fields as core_fields
from creme.creme_core.models import CREME_REPLACE
from creme.creme_core.models.currency import get_default_currency_pk


class Migration(migrations.Migration):
    # Memo: last migration was "0028_v2_6__fix_statuses_uuids"
    initial = True
    dependencies = [
        ('creme_core', '0001_initial'),
        migrations.swappable_dependency(settings.ACTIVITIES_ACTIVITY_MODEL),
        migrations.swappable_dependency(settings.PERSONS_CONTACT_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ProjectStatus',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                ('color_code', core_fields.ColorField(max_length=6, verbose_name='Color', blank=True)),
                ('description', models.TextField(verbose_name='Description')),
                ('order', core_fields.BasicAutoField(editable=False, blank=True)),
                ('extra_data', models.JSONField(default=dict, editable=False)),
                ('is_custom', models.BooleanField(default=True, editable=False)),
                ('uuid', models.UUIDField(default=uuid4, editable=False, unique=True)),
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
                (
                    'cremeentity_ptr',
                    models.OneToOneField(
                        to='creme_core.CremeEntity', primary_key=True,
                        parent_link=True, auto_created=True, serialize=False,
                        on_delete=CASCADE,
                    )
                ),
                ('name', models.CharField(max_length=100, verbose_name='Name of the project')),
                ('start_date', models.DateTimeField(null=True, verbose_name='Estimated start', blank=True)),
                ('end_date', models.DateTimeField(null=True, verbose_name='Estimated end', blank=True)),
                (
                    'effective_end_date',
                    models.DateTimeField(
                        null=True, verbose_name='Effective end date', blank=True, editable=False,
                    )
                ),
                (
                    'status',
                    models.ForeignKey(
                        to='projects.ProjectStatus',
                        on_delete=CREME_REPLACE, verbose_name='Status',
                    )
                ),
                (
                    'currency',
                    models.ForeignKey(
                        related_name='+', on_delete=PROTECT,
                        # default=1,
                        default=get_default_currency_pk,
                        verbose_name='Currency', to='creme_core.Currency',
                    )
                ),
            ],
            options={
                'swappable': 'PROJECTS_PROJECT_MODEL',
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
                ('color_code', core_fields.ColorField(max_length=6, verbose_name='Color', blank=True)),
                ('description', models.TextField(verbose_name='Description')),
                ('is_custom', models.BooleanField(default=True, editable=False)),
                ('order', core_fields.BasicAutoField(editable=False, blank=True)),
                ('extra_data', models.JSONField(default=dict, editable=False)),
                ('uuid', models.UUIDField(default=uuid4, editable=False, unique=True)),
            ],
            options={
                'ordering': ('order',),
                'verbose_name': 'Status of task',
                'verbose_name_plural': 'Status of task',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ProjectTask',
            fields=[
                (
                    'cremeentity_ptr',
                    models.OneToOneField(
                        to='creme_core.CremeEntity', primary_key=True,
                        parent_link=True, auto_created=True, serialize=False,
                        on_delete=CASCADE,
                    )
                ),
                ('title', models.CharField(max_length=100, verbose_name='Title')),
                (
                    'linked_project',
                    models.ForeignKey(
                        verbose_name='Project', to=settings.PROJECTS_PROJECT_MODEL,
                        related_name='tasks_set', editable=False, on_delete=CASCADE,
                    )
                 ),
                ('order', models.PositiveIntegerField(verbose_name='Order', editable=False)),
                (
                    'parent_tasks',
                    models.ManyToManyField(
                        to=settings.PROJECTS_TASK_MODEL,
                        related_name='children', editable=False,
                    )
                ),
                ('start', models.DateTimeField(verbose_name='Start')),
                ('end', models.DateTimeField(verbose_name='End')),
                ('duration', models.PositiveIntegerField(default=0, verbose_name='Duration (in hours)')),
                (
                    'tstatus',
                    models.ForeignKey(
                        to='projects.TaskStatus',
                        on_delete=CREME_REPLACE, verbose_name='Task situation',
                    )
                ),
            ],
            options={
                'swappable': 'PROJECTS_TASK_MODEL',
                'ordering': ('-start',),
                'verbose_name': 'Task of project',
                'verbose_name_plural': 'Tasks of project',
            },
            bases=('creme_core.CremeEntity',),
        ),
        migrations.CreateModel(
            name='Resource',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('hourly_cost', models.PositiveIntegerField(default=0, verbose_name='Hourly cost')),
                (
                    'linked_contact',
                    models.ForeignKey(
                        to=settings.PERSONS_CONTACT_MODEL,
                        editable=False, verbose_name='Contact', on_delete=CASCADE,
                    )
                ),
                (
                    'task',
                    models.ForeignKey(
                        to='projects.ProjectTask', verbose_name='Task',
                        related_name='resources_set', editable=False, on_delete=CASCADE,
                    )
                ),
            ],
            options={
                'verbose_name': 'Resource of project',
                'verbose_name_plural': 'Resources of project',
            },
            bases=(models.Model,),
        ),
    ]
