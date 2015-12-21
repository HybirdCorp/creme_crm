# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations  # models


def fix_old_mysql_constraint(apps, schema_editor):
    db_settings = settings.DATABASES['default']

    if 'mysql' in db_settings['ENGINE']:
        connection = schema_editor.connection
        # We need an internal cursor, because the django api has no fetchall() method...
        lowlevel_cursor = connection.cursor().cursor.cursor

        lowlevel_cursor.execute("SHOW CREATE TABLE auth_user")
        creation_cmd =  lowlevel_cursor.fetchall()[0][1]

        start_idx = creation_cmd.find('role_id_refs_id_')

        if start_idx != -1:  # Ok this is an old 1.5 DB install, we have to remove the constraint
            end_idx = creation_cmd.find('`', start_idx)
            constraint_name = creation_cmd[start_idx: end_idx]

            lowlevel_cursor.execute("ALTER TABLE `auth_user` DROP FOREIGN KEY `%s`" % constraint_name)


class Migration(migrations.Migration):
    dependencies = [
        ('auth', '0002_v1_6__django18_fixes'),
        ('creme_core', '0003_v1_6__convert_old_users'),
    ]

    operations = [
        migrations.RunPython(fix_old_mysql_constraint),
        migrations.RemoveField(
            model_name='user',
            name='is_team',
        ),
        migrations.RemoveField(
            model_name='user',
            name='role_id',
        ),
        # migrations.AlterField(
        #     model_name='user',
        #     name='groups',
        #     field=models.ManyToManyField(related_query_name='user', related_name='user_set', to='auth.Group', blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', verbose_name='groups'),
        # ),
    ]
