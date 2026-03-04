import uuid

from django.conf import settings
from django.db import migrations, models
from django.db.models.deletion import CASCADE, PROTECT

import creme.creme_core.models.fields as core_fields
from creme.creme_core.core.entity_filter import EF_REGULAR
from creme.reports.constants import EF_REPORTS


class Migration(migrations.Migration):
    # replaces = [
    #     ('reports', '0001_initial'),
    #     ('reports', '0014_v2_7__portable_report_field'),
    #     ('reports', '0015_v2_7__portable_graph'),
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
                (
                    'cremeentity_ptr',
                    models.OneToOneField(
                        parent_link=True, auto_created=True, primary_key=True, serialize=False,
                        to='creme_core.CremeEntity', on_delete=CASCADE,
                    )
                ),
                ('name', models.CharField(max_length=100, verbose_name='Name of the report')),
                (
                    'ct',
                    core_fields.EntityCTypeForeignKey(verbose_name='Entity type', to='contenttypes.ContentType')
                ),
                (
                    'filter',
                    models.ForeignKey(
                        on_delete=PROTECT, verbose_name='Filter', blank=True,
                        to='creme_core.EntityFilter', null=True,
                        limit_choices_to={'filter_type__in': [EF_REGULAR, EF_REPORTS]},
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
                ('name', models.CharField(max_length=100)),
                ('order', models.PositiveIntegerField()),
                ('type', models.PositiveSmallIntegerField()),
                ('selected', models.BooleanField(default=False)),
                (
                    'report',
                    models.ForeignKey(related_name='fields', to=settings.REPORTS_REPORT_MODEL, on_delete=CASCADE)
                ),
                (
                    'sub_report',
                    models.ForeignKey(blank=True, to=settings.REPORTS_REPORT_MODEL, null=True, on_delete=CASCADE)
                ),
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
                (
                    'cremeentity_ptr',
                    models.OneToOneField(
                        parent_link=True, auto_created=True, primary_key=True, serialize=False,
                        to='creme_core.CremeEntity', on_delete=CASCADE,
                    )
                ),
                ('name', models.CharField(max_length=100, verbose_name='Name of the chart')),
                (
                    'abscissa_cell_value',
                    models.CharField(verbose_name='X axis (field)', max_length=100, editable=False)
                ),
                (
                    'abscissa_parameter',
                    models.TextField(verbose_name='X axis parameter', editable=False, null=True)
                ),
                (
                    'ordinate_type',
                    models.CharField(
                        verbose_name='Y axis (type)', editable=False, max_length=100, default='',
                        choices=[
                            ('count', 'Count'), ('avg', 'Average'), ('max', 'Maximum'),
                            ('min', 'Minimum'), ('sum', 'Sum'),
                        ],
                    )
                ),
                (
                    'ordinate_cell_key',
                    models.CharField(verbose_name='Y axis (field)', editable=False, max_length=100, default='')
                ),
                (
                    'abscissa_type',
                    models.PositiveIntegerField(
                        verbose_name='X axis (grouping)', editable=False,
                        choices=[
                            (1, 'By days'), (2, 'By months'), (3, 'By years'), (4, 'By X days'),
                            (5, 'By values (configurable)'),
                            (6, 'By values (of related entities)'),
                            (7, 'By values (not configurable)'),
                            (11, 'By days (custom field)'), (12, 'By months (custom field)'),
                            (13, 'By years (custom field)'), (14, 'By X days (custom field)'),
                            (15, 'By values (of custom choices)'),
                        ],
                    )
                ),
                ('chart', models.CharField(max_length=100, null=True, verbose_name='Chart type')),
                ('asc', models.BooleanField(default=True, editable=False, verbose_name='ASC order')),
                (
                    'linked_report',
                    models.ForeignKey(editable=False, to=settings.REPORTS_REPORT_MODEL, on_delete=CASCADE)
                ),
            ],
            options={
                'swappable': 'REPORTS_GRAPH_MODEL',
                'ordering': ['name'],
                'verbose_name': 'Report chart',
                'verbose_name_plural': 'Report charts',
            },
            bases=('creme_core.cremeentity',),
        ),
    ]

    if settings.TESTS_ON:
        operations.extend([
            migrations.CreateModel(
                name='FakeReportsFolder',
                fields=[
                    (
                        'cremeentity_ptr',
                        models.OneToOneField(
                            parent_link=True, auto_created=True, primary_key=True, serialize=False,
                            to='creme_core.CremeEntity', on_delete=CASCADE,
                        )
                    ),
                    ('title', models.CharField(unique=True, max_length=100, verbose_name='Title')),
                    (
                        'parent',
                        models.ForeignKey(
                            on_delete=PROTECT, verbose_name='Parent folder',
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
                name='FakeReportsColorCategory',
                fields=[
                    ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                    ('is_custom', models.BooleanField(default=True)),
                    ('extra_data', models.JSONField(default=dict, editable=False)),
                    ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                    ('title', models.CharField(max_length=100, verbose_name='Title')),
                    (
                        'color',
                        core_fields.ColorField(
                            default=core_fields.ColorField.random,
                            max_length=6, verbose_name='Color',
                        )
                    ),
                ],
                options={
                    'ordering': ('title',),
                    'verbose_name': 'Test (reports) Color Category',
                    'verbose_name_plural': 'Test (reports) Color Categories',
                },
                bases=(models.Model,),
            ),
            migrations.CreateModel(
                name='FakeReportsDocument',
                fields=[
                    (
                        'cremeentity_ptr',
                        models.OneToOneField(
                            parent_link=True, auto_created=True, primary_key=True, serialize=False,
                            to='creme_core.CremeEntity', on_delete=CASCADE,
                        )
                    ),
                    ('title', models.CharField(max_length=100, verbose_name='Title')),
                    (
                        'linked_folder',
                        models.ForeignKey(
                            on_delete=PROTECT, verbose_name='Folder', to='reports.FakeReportsFolder',
                        )
                    ),
                    (
                        'category',
                        models.ForeignKey(
                            on_delete=PROTECT, verbose_name='Category', to='reports.FakeReportsColorCategory',
                            null=True,
                        )
                    ),
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
                    (
                        'cremeentity_ptr',
                        models.OneToOneField(
                            parent_link=True, auto_created=True, primary_key=True, serialize=False,
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
