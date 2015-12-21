# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


def remove_old_ctype(apps, schema_editor):
    apps.get_model('contenttypes', 'ContentType').objects.filter(app_label='projects',
                                                                 model='workingperiod',
                                                                ) \
                                                         .delete()



class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0008_v1_6_fix_reports_with_tasks_set'),
    ]

    operations = [
        migrations.RunPython(remove_old_ctype),
    ]
