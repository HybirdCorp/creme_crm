# -*- coding: utf-8 -*-

from django.conf import settings
from django.db import models, migrations
from django.db.models.deletion import PROTECT, CASCADE

from creme.creme_core.models import fields as creme_fields

EF_USER = 1


class Migration(migrations.Migration):
    # replaces = [
    #     ('reports', '0001_initial'),
    #     ('reports', '0004_v1_8__linked_report_field'),
    #     ('reports', '0005_v1_8__document_linked_folder'),
    # ]

    initial = True
    dependencies = [
        ('creme_core', '0001_initial'),
        ('contenttypes', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Report',
            fields=[
                ('cremeentity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False,
                                                         to='creme_core.CremeEntity', on_delete=CASCADE,
                                                        )
                ),
                ('name', models.CharField(max_length=100, verbose_name='Name of the report')),
                ('ct', creme_fields.EntityCTypeForeignKey(verbose_name='Entity type', to='contenttypes.ContentType')),
                ('filter', models.ForeignKey(on_delete=PROTECT, verbose_name='Filter', blank=True,
                                             to='creme_core.EntityFilter', null=True,
                                             limit_choices_to={'filter_type': EF_USER},
                                            )
                ),
            ],
            options={
                'swappable': 'REPORTS_REPORT_MODEL',
                'ordering': ('name',),
                'verbose_name': 'Report',
                'verbose_name_plural': 'Reports',
            },
            bases=('creme_core.cremeentity',),
        ),
        migrations.CreateModel(
            name='Field',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100, verbose_name='Name of the column')),
                ('order', models.PositiveIntegerField()),
                ('type', models.PositiveSmallIntegerField()),
                ('selected', models.BooleanField(default=False)),
                ('report', models.ForeignKey(related_name='fields', to=settings.REPORTS_REPORT_MODEL, on_delete=CASCADE)),
                ('sub_report', models.ForeignKey(blank=True, to=settings.REPORTS_REPORT_MODEL, null=True, on_delete=CASCADE,)),
            ],
            options={
                'ordering': ('order',),
                'verbose_name': 'Column of report',
                'verbose_name_plural': 'Columns of report',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ReportGraph',
            fields=[
                ('cremeentity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False,
                                                         to='creme_core.CremeEntity', on_delete=CASCADE,
                                                        )
                ),
                ('name', models.CharField(max_length=100, verbose_name='Name of the graph')),
                ('abscissa', models.CharField(verbose_name='X axis', max_length=100, editable=False)),
                ('ordinate', models.CharField(verbose_name='Y axis', max_length=100, editable=False)),
                ('type', models.PositiveIntegerField(verbose_name='Grouping', editable=False,
                                                     choices=[(1, 'By days'), (2, 'By months'), (3, 'By years'), (4, 'By X days'),
                                                              (5, 'By values'), (6, 'By values (of related entities)'),
                                                              (11, 'By days (custom field)'), (12, 'By months (custom field)'),
                                                              (13, 'By years (custom field)'), (14, 'By X days (custom field)'),
                                                              (15, 'By values (of custom choices)'),
                                                             ],
                                                    )
                ),
                ('days', models.PositiveIntegerField(null=True, verbose_name='Days', blank=True)),
                ('is_count', models.BooleanField(default=False, verbose_name='Make a count instead of aggregate?')),
                ('chart', models.CharField(max_length=100, null=True, verbose_name='Chart type')),
                # ('report', models.ForeignKey(editable=False, to=settings.REPORTS_REPORT_MODEL, on_delete=CASCADE)),
                ('linked_report', models.ForeignKey(editable=False, to=settings.REPORTS_REPORT_MODEL, on_delete=CASCADE)),
            ],
            options={
                'swappable': 'REPORTS_GRAPH_MODEL',
                'ordering': ['name'],
                'verbose_name': "Report's graph",
                'verbose_name_plural': "Reports' graphs",
            },
            bases=('creme_core.cremeentity',),
        ),
    ]

    if settings.TESTS_ON:
        operations.extend([
            migrations.CreateModel(
                name='FakeReportsFolder',
                fields=[
                    ('cremeentity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False,
                                                             to='creme_core.CremeEntity', on_delete=CASCADE,
                                                            )
                    ),
                    ('title', models.CharField(unique=True, max_length=100, verbose_name='Title')),
                    # ('description', models.TextField(null=True, verbose_name='Description', blank=True)),
                    ('parent', models.ForeignKey(on_delete=PROTECT, verbose_name='Parent folder',
                                                 to='reports.FakeReportsFolder', null=True,
                                                )
                    ),
                ],
                options={
                    'ordering': ('title',),
                    'verbose_name': 'Test (reports) Folder',
                    'verbose_name_plural': 'Test (reports) Folders',
                },
                bases=('creme_core.cremeentity',),
            ),
            migrations.CreateModel(
                name='FakeReportsDocument',
                fields=[
                    ('cremeentity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False,
                                                             to='creme_core.CremeEntity', on_delete=CASCADE,
                                                            )
                    ),
                    ('title', models.CharField(max_length=100, verbose_name='Title')),
                    # ('description', models.TextField(null=True, verbose_name='Description', blank=True)),
                    ('linked_folder', models.ForeignKey(on_delete=PROTECT, verbose_name='Folder', to='reports.FakeReportsFolder')),
                ],
                options={
                    'ordering': ('title',),
                    'verbose_name': 'Test (reports) Document',
                    'verbose_name_plural': 'Test (reports) Documents',
                },
                bases=('creme_core.cremeentity',),
            ),
            migrations.CreateModel(
                name='Guild',
                fields=[
                    ('cremeentity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False,
                                                             to='creme_core.CremeEntity', on_delete=CASCADE,
                                                            )
                    ),
                    ('name', models.CharField(max_length=100, verbose_name='Name')),
                    ('members', models.ManyToManyField(to='creme_core.FakeContact', verbose_name='Members')),
                ],
                options={
                    'ordering': ('name',),
                    'verbose_name': 'Book',
                    'verbose_name_plural': 'Books',
                },
                bases=('creme_core.cremeentity',),
            ),
        ])
