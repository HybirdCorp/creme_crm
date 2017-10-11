# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations


PSTATUS_FIELDS = ['color_code']
TSTATUS_FIELDS = ['color_code']
PROJECT_FIELDS = ['description']
TASK_FIELDS = ['description']


def fill_none_strings(apps, schema_editor):
    def migrate_model(name, fields):
        manager = apps.get_model('projects', name).objects

        for field_name in fields:
            manager.filter(**{field_name: None}).update(**{field_name: ''})

    migrate_model('ProjectStatus', PSTATUS_FIELDS)
    migrate_model('TaskStatus',    TSTATUS_FIELDS)

    if settings.PROJECTS_PROJECT_MODEL == 'projects.Project':
        migrate_model('Project', PROJECT_FIELDS)

    if settings.PROJECTS_TASK_MODEL == 'projects.ProjectTask':
        migrate_model('Project', TASK_FIELDS)


class Migration(migrations.Migration):
    dependencies = [
        # ('projects', '0009_v1_6__clean_ctype'),
        ('projects', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(fill_none_strings),
    ]
