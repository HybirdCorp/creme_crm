# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from collections import defaultdict

from django.db import migrations


def rename_roles_with_same_same(apps, schema_editor):
    UserRole = apps.get_model('creme_core', 'UserRole')
    MAX_LEN = UserRole._meta.get_field('name').max_length

    roles_info = defaultdict(list)
    for role_id, role_name in UserRole.objects.values_list('id', 'name'):
        roles_info[role_name].append(role_id)

    for role_name, roles_ids in roles_info.items():  # NB: not iteritems() in order to modify 'roles_info'
        if len(roles_ids) == 1:
            continue

        for role_id in roles_ids[1:]:
            for i in xrange(2, 101):
                new_role_name = '{}#{}'.format(role_name, i)

                if len(new_role_name) > MAX_LEN:
                    raise ValueError('The roles with name="{}" cannot be renamed safely ; '
                                     'rename it manually (its name should be unique) before running the migrations.'.format(role_name)
                                     )

                if new_role_name not in roles_info:
                    UserRole.objects.filter(id=role_id).update(name=new_role_name)
                    roles_info[new_role_name].append(role_id)
                    break
            else:
                raise ValueError('The roles with name="{}" cannot be renamed safely ; '
                                 'rename it manually (its name should be unique) before running the migrations.'.format(role_name)
                                 )


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0023_v1_7__rm_merge_button'),
    ]

    operations = [
        migrations.RunPython(rename_roles_with_same_same),
    ]
