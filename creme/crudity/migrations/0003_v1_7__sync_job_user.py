# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations


def set_user(apps, schema_editor):
    Job = apps.get_model('creme_core', 'Job')

    try:
        job = Job.objects.get(type_id='crudity-synchronization')
    except Job.DoesNotExist:
        pass
    else:
        user_id = getattr(settings, 'CREME_GET_EMAIL_JOB_USER_ID', None)
        if user_id is not None:
            job.raw_data = '{"user": %s}' % user_id
            job.save()


class Migration(migrations.Migration):
    dependencies = [
        # ('crudity', '0002_v1_6__convert_user_FKs'),
        ('crudity', '0001_initial'),
        ('creme_core', '0015_v1_7__create_job_models'),
    ]

    operations = [
        migrations.RunPython(set_user),
    ]
