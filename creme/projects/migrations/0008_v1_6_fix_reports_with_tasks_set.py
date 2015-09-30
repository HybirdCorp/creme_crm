# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


RFT_RELATED = 7

def fix_reports(apps, schema_editor):
    get_model = apps.get_model

    ContentType = get_model('contenttypes', 'ContentType')

    project_ctype = ContentType.objects.filter(app_label='projects', model='project').first()

    if project_ctype is not None:
        # NB: it seems the query does not work with 'project_ctype' instance -> we use its ID
        get_model('reports', 'Field').objects.filter(report__ct=project_ctype.id,
                                                     type=RFT_RELATED,
                                                     name='projecttask',
                                                    ) \
                                             .update(name='tasks_set')


class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0007_v1_6__change_activities_block_id'),
        ('reports', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(fix_reports),
    ]
