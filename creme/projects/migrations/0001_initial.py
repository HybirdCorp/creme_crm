# -*- coding: utf-8 -*-

from django.conf import settings
from django.db import migrations, models
from django.db.models.deletion import CASCADE, PROTECT

from creme.creme_core.models import CREME_REPLACE
from creme.creme_core.models import fields as creme_fields


class Migration(migrations.Migration):
    # replaces = [
    #     ('projects', '0001_initial'),
    #     ('projects', '0019_v2_2__task_start_end_duration_notnull'),
    #     ('projects', '0020_v2_2__resource_not_entity01'),
    #     ('projects', '0021_v2_2__resource_not_entity02'),
    #     ('projects', '0022_v2_2__resource_not_entity03'),
    #     ('projects', '0023_v2_2__resource_not_entity04'),
    # ]

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
                ('color_code', creme_fields.ColorField(max_length=6, verbose_name='Color', blank=True)),
                ('description', models.TextField(verbose_name='Description')),
                ('order', creme_fields.BasicAutoField(verbose_name='Order', editable=False, blank=True)),
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
                ('cremeentity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False,
                                                         to='creme_core.CremeEntity', on_delete=CASCADE,
                                                        )
                ),
                ('name', models.CharField(max_length=100, verbose_name='Name of the project')),
                ('start_date', models.DateTimeField(null=True, verbose_name='Estimated start', blank=True)),
                ('end_date', models.DateTimeField(null=True, verbose_name='Estimated end', blank=True)),
                ('effective_end_date', models.DateTimeField(null=True, verbose_name='Effective end date', blank=True, editable=False)),
                ('status', models.ForeignKey(on_delete=CREME_REPLACE, verbose_name='Status', to='projects.ProjectStatus')),
                ('currency', models.ForeignKey(related_name='+', on_delete=PROTECT, default=1,
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
                ('color_code', creme_fields.ColorField(max_length=6, verbose_name='Color', blank=True)),
                ('description', models.TextField(verbose_name='Description')),
                ('is_custom', models.BooleanField(default=True)),
                ('order', creme_fields.BasicAutoField(verbose_name='Order', editable=False, blank=True)),
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
                ('cremeentity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False,
                                                         to='creme_core.CremeEntity', on_delete=CASCADE,
                                                        )
                ),
                ('title', models.CharField(max_length=100, verbose_name='Title')),
                ('linked_project', models.ForeignKey(related_name='tasks_set', editable=False,
                                                     to=settings.PROJECTS_PROJECT_MODEL,
                                                     verbose_name='Project', on_delete=CASCADE,
                                                    )
                 ),
                ('order', models.PositiveIntegerField(verbose_name='Order', null=True, editable=False, blank=True)),
                # ('parent_tasks', models.ManyToManyField(related_name='children_set', editable=False, to=settings.PROJECTS_TASK_MODEL)),
                ('parent_tasks', models.ManyToManyField(related_name='children', editable=False, to=settings.PROJECTS_TASK_MODEL)),
                # ('start', models.DateTimeField(null=True, verbose_name='Start', blank=True)),
                ('start', models.DateTimeField(verbose_name='Start')),
                # ('end',   models.DateTimeField(null=True, verbose_name='End', blank=True)),
                ('end', models.DateTimeField(verbose_name='End')),
                # ('duration', models.PositiveIntegerField(null=True, verbose_name='Duration (in hours)', blank=True)),
                ('duration', models.PositiveIntegerField(default=0, verbose_name='Duration (in hours)')),
                # ('description', models.TextField(verbose_name='Description', blank=True)),
                ('tstatus', models.ForeignKey(on_delete=CREME_REPLACE, verbose_name='Task situation', to='projects.TaskStatus')),
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
                # ('cremeentity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False,
                #                                          to='creme_core.CremeEntity', on_delete=CASCADE,
                #                                         )
                # ),
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('hourly_cost', models.PositiveIntegerField(default=0, verbose_name='Hourly cost')),
                ('linked_contact', models.ForeignKey(editable=False, to=settings.PERSONS_CONTACT_MODEL, verbose_name='Contact', on_delete=CASCADE)),
                ('task', models.ForeignKey(related_name='resources_set', editable=False, to='projects.ProjectTask', verbose_name='Task', on_delete=CASCADE)),
            ],
            options={
                'verbose_name': 'Resource of project',
                'verbose_name_plural': 'Resources of project',
            },
            # bases=('creme_core.cremeentity',),
            bases=(models.Model,),
        ),
    ]
