# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import models, migrations, connection


deferred_queries = []


# MySQL (at least the 5.5 family) does not like that we change activity_ptr in
# cremeentity_ptr (the removing of activity_ptr indeed), because of contraints
# of ForeignKeys referencing ProjectTasks => we have to rebuild these contraints.
def delete_mysql_fucking_constraints(apps, schema_editor):

    if 'mysql' in settings.DATABASES['default']['ENGINE']:
        if settings.PROJECTS_TASK_MODEL != 'projects.ProjectTask':
            print 'Error in projects/migrations/0004_v1_6__new_task_model_n_remove_wperiod_3.py delete_mysql_fucking_constraints():' \
                 ' cannot use ProjectTask because the model is custom. You should fix it with your custom model.'
            return

        import re

        regex = re.compile('CONSTRAINT `(?P<constraint>.*)` FOREIGN KEY \(`(?P<field>.*)`\) REFERENCES `projects_projecttask`')
        cursor = connection.cursor()

        def manage_model_FKs(model_name):
            cursor.execute('SHOW CREATE TABLE projects_%s' % model_name)
            creation_cmd = cursor.fetchone()[1]

            for mo in regex.finditer(creation_cmd):
                gdict = mo.groupdict()
                constraint_name = gdict['constraint']
                cursor.execute("ALTER TABLE `projects_%s` DROP FOREIGN KEY `%s`" % (model_name, constraint_name))
                deferred_queries.append("ALTER TABLE `projects_%(model)s` ADD CONSTRAINT `%(constraint)s` FOREIGN KEY ( `%(field)s` ) "
                                        "REFERENCES `projects_projecttask` ( `cremeentity_ptr_id` ) ON DELETE RESTRICT ON UPDATE RESTRICT" % {
                                            'model': model_name,
                                            'constraint': constraint_name,
                                            'field': gdict['field'],
                                        }
                                       )

        manage_model_FKs('resource')
        manage_model_FKs('workingperiod')
        manage_model_FKs('projecttask_parent_tasks')

def rebuild_mysql_fucking_constraints(apps, schema_editor):
    if 'mysql' in settings.DATABASES['default']['ENGINE']:
        cursor = connection.cursor()

        for query in deferred_queries:
            cursor.execute(query)


class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0003_v1_6__new_task_model_n_remove_wperiod_2'),
    ]

    operations = [
        migrations.RunPython(delete_mysql_fucking_constraints),

        migrations.RemoveField(
            model_name='projecttask',
            name='activity_ptr',
        ),

        # FK to CremeEntity is finalized : not nullable, primary key
        migrations.AlterField(
            model_name='projecttask',
            name='cremeentity_ptr',
            field=models.OneToOneField(parent_link=True, # (+ 'bases' in 0001_initial.py) in Creme1.7
                                       #parent_link=False,
                                       auto_created=True,
                                       primary_key=True,
                                       serialize=False,
                                       #null=False,
                                       to='creme_core.CremeEntity',
                                      ),
            preserve_default=True,
        ),

        migrations.RunPython(rebuild_mysql_fucking_constraints),

        # 'title' field is finalized (no default value anymore).
        migrations.AlterField(
            model_name='projecttask',
            name='title',
            field=models.CharField(max_length=100, verbose_name='Title'),
            preserve_default=True,
        ),

        # Remove the model WorkingPeriod
        migrations.RemoveField(
            model_name='workingperiod',
            name='resource',
        ),
        migrations.RemoveField(
            model_name='workingperiod',
            name='task',
        ),
        migrations.DeleteModel(
            name='WorkingPeriod',
        ),
    ]
