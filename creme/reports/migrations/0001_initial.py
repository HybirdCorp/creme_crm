# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import models, migrations
import django.db.models.deletion

import creme.creme_core.models.fields


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0001_initial'),
        ('contenttypes', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Report',
            fields=[
                ('cremeentity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='creme_core.CremeEntity')),
                ('name', models.CharField(max_length=100, verbose_name='Name of the report')),
                ('ct', creme.creme_core.models.fields.EntityCTypeForeignKey(verbose_name='Entity type', to='contenttypes.ContentType')),
                ('filter', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, verbose_name='Filter', blank=True, to='creme_core.EntityFilter', null=True)),
            ],
            options={
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
                ('report', models.ForeignKey(related_name='fields', to='reports.Report')),
                ('sub_report', models.ForeignKey(blank=True, to='reports.Report', null=True)),
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
                ('cremeentity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='creme_core.CremeEntity')),
                ('name', models.CharField(max_length=100, verbose_name='Name of the graph')),
                ('abscissa', models.CharField(verbose_name='Abscissa axis', max_length=100, editable=False)),
                ('ordinate', models.CharField(verbose_name='Ordinate axis', max_length=100, editable=False)),
                ('type', models.PositiveIntegerField(verbose_name='Type', editable=False)),
                ('days', models.PositiveIntegerField(null=True, verbose_name='Days', blank=True)),
                ('is_count', models.BooleanField(default=False, verbose_name='Make a count instead of aggregate?')),
                ('chart', models.CharField(max_length=100, null=True, verbose_name='Chart type')),
                ('report', models.ForeignKey(editable=False, to='reports.Report')),
            ],
            options={
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
                name='FakeFolder',
                fields=[
                    ('cremeentity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='creme_core.CremeEntity')),
                    ('title', models.CharField(unique=True, max_length=100, verbose_name='Title')),
                    ('description', models.TextField(null=True, verbose_name='Description', blank=True)),
                ],
                options={
                    'ordering': ('title',),
                    'verbose_name': 'Test Folder',
                    'verbose_name_plural': 'Test Folders',
                },
                bases=('creme_core.cremeentity',),
            ),
            migrations.CreateModel(
                name='FakeDocument',
                fields=[
                    ('cremeentity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='creme_core.CremeEntity')),
                    ('title', models.CharField(max_length=100, verbose_name='Title')),
                    ('description', models.TextField(null=True, verbose_name='Description', blank=True)),
                    ('folder', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, verbose_name='Folder', to='reports.FakeFolder')),
                ],
                options={
                    'ordering': ('title',),
                    'verbose_name': 'Test Document',
                    'verbose_name_plural': 'Test Documents',
                },
                bases=('creme_core.cremeentity',),
            ),
        ])
