# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, connection

from creme.activities.constants import REL_SUB_PART_2_ACTIVITY

from .. import task_model_is_custom


def delete_old_task_activities(apps, schema_editor):
    if task_model_is_custom():
        print 'Error in projects/migrations/0005_v1_6__new_task_model_n_remove_wperiod_4.py delete_old_task_activities():' \
                ' cannot use ProjectTask because the model is custom. You should fix it with your custom model.'
        return

    get_model = apps.get_model
    ids = list(get_model('projects', 'ProjectTask').objects
                                                   #.values_list('activity_ptr', flat=True)
                                                   .values_list('cremeentity_ptr', flat=True)
              )

    if ids:
        get_model('creme_core', 'Relation').objects.filter(type=REL_SUB_PART_2_ACTIVITY,
                                                           object_entity__in=ids,
                                                          ) \
                                                   .delete()

        # NB: we cannot just delete activities like that, because it would delete the entity part too
        # get_model('activities', 'Activity').objects.filter(id__in=ids).delete()
        cursor = connection.cursor()
        cursor.execute('DELETE FROM activities_activity WHERE cremeentity_ptr_id IN (%s)' %
                            ','.join(str(i) for i in ids)
                      )


class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0004_v1_6__new_task_model_n_remove_wperiod_3'),
    ]

    operations = [
        migrations.RunPython(delete_old_task_activities),
    ]
