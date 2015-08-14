# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from collections import defaultdict

from django.db import migrations


def update_configs(apps, schema_editor):
    SearchConfigItem = apps.get_model('creme_core', 'SearchConfigItem')
    sc_items_per_ctid = defaultdict(list)
    first_print = True

    for sci in SearchConfigItem.objects.exclude(user__isnull=True):
        sc_items_per_ctid[sci.content_type_id].append(sci)

    for ct_id, ct_scitems in sc_items_per_ctid.iteritems():
        scitems_per_role = defaultdict(list)

        for sci in ct_scitems:
            user = sci.user

            if user.is_team: # versions < 1.5.4  allowed teams...
                sci.delete()
            else:
                scitems_per_role[user.role].append(sci)

        for role, role_scitems in scitems_per_role.iteritems():
            scitem = role_scitems[0]
            scitem.role = role
            scitem.superuser = (role is None)
            scitem.save()

            for scitem in role_scitems[1:]:
                if first_print:
                    print('\n')
                    first_print = False

                print('The search config for user="%s" content_type="%s.%s" has to be dropped.' % (
                            scitem.user.username,
                            scitem.content_type.app_label,
                            scitem.content_type.model,
                        )
                     )
                scitem.delete()


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0006_v1_6__searchconfig_per_role_1'),
    ]

    operations = [
        migrations.RunPython(update_configs),
    ]
