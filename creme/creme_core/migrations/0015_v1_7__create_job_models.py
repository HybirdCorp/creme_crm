# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings

import creme.creme_core.models.fields


class Migration(migrations.Migration):
    dependencies = [
        # ('creme_core', '0014_v1_6__set_version'),
        ('creme_core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Job',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('type_id', models.CharField(verbose_name='Type of job', max_length=48, editable=False)),
                ('enabled', models.BooleanField(default=True, verbose_name='Enabled', editable=False)),
                ('language', models.CharField(verbose_name='Language', max_length=10, editable=False)),
                ('reference_run', models.DateTimeField(verbose_name='Reference run')),
                ('periodicity', creme.creme_core.models.fields.DatePeriodField(null=True, verbose_name='Periodicity')),
                ('last_run', models.DateTimeField(verbose_name='Last run', null=True, editable=False)),
                ('ack_errors', models.PositiveIntegerField(default=0, editable=False)),
                ('status', models.PositiveSmallIntegerField(default=1, verbose_name='Status', editable=False,
                                                            choices=[(1, 'Waiting'),
                                                                     (10, 'Error'),
                                                                     (20, 'Completed successfully'),
                                                                    ],
                                                           )
                ),
                ('error', models.TextField(verbose_name='Error', null=True, editable=False)),
                ('raw_data', models.TextField(editable=False)),
                ('user', creme.creme_core.models.fields.CremeUserForeignKey(editable=False, to=settings.AUTH_USER_MODEL, null=True, verbose_name='User')),
            ],
            options={
                'ordering': ('id',),
                'verbose_name': 'Job',
                'verbose_name_plural': 'Jobs',
            },
        ),
        migrations.CreateModel(
            name='JobResult',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('raw_messages', models.TextField(null=True)),
                ('job', models.ForeignKey(to='creme_core.Job')),
            ],
            options={},
        ),
        migrations.CreateModel(
            name='EntityJobResult',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('raw_messages', models.TextField(null=True)),
                ('entity', models.ForeignKey(to='creme_core.CremeEntity', null=True)),
                ('job', models.ForeignKey(to='creme_core.Job')),
            ],
            options={},
        ),
        migrations.CreateModel(
            name='MassImportJobResult',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('raw_messages', models.TextField(null=True)),
                ('raw_line', models.TextField()),
                ('updated', models.BooleanField(default=False)),
                ('entity', models.ForeignKey(to='creme_core.CremeEntity', null=True)),
                ('job', models.ForeignKey(to='creme_core.Job')),
            ],
            options={},
        ),
    ]
