# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from collections import defaultdict
from uuid import uuid4

from django.db import migrations


def fill_UUIDs(apps, schema_editor):
    for cfield in apps.get_model('creme_core', 'CustomField').objects.all():
        cfield.uuid = uuid4()
        cfield.save()


def rename_cfields_with_same_same(apps, schema_editor):
    CustomField = apps.get_model('creme_core', 'CustomField')
    MAX_LEN = CustomField._meta.get_field('name').max_length

    cfields_info = defaultdict(list)
    for cfield_id, cfield_name, cfield_ctid in CustomField.objects.values_list('id', 'name', 'content_type_id'):
        cfields_info[(cfield_name, cfield_ctid)].append(cfield_id)

    for (cfield_name, cfield_ctid), cfields_ids in cfields_info.items():  # NB: not iteritems() in order to modify 'cfields_info'
        if len(cfields_ids) == 1:
            continue

        for cfield_id in cfields_ids[1:]:
            for i in xrange(2, 101):
                new_cfield_name = '{}#{}'.format(cfield_name, i)

                if len(new_cfield_name) > MAX_LEN:
                    raise ValueError('The CustomField with name="{}" cannot be renamed safely ; '
                                     'rename it manually (its name should be unique for one given content_type) '
                                     'before running the migrations.'.format(cfield_name)
                                     )

                new_key = (new_cfield_name, cfield_ctid)
                if new_key not in cfields_info:
                    CustomField.objects.filter(id=cfield_id).update(name=new_cfield_name)
                    cfields_info[new_key].append(cfield_id)
                    break
            else:
                raise ValueError('The CustomField with name="{}" cannot be renamed safely ; '
                                 'rename it manually (its name should be unique for one given content_type) '
                                 'before running the migrations.'.format(cfield_name)
                                )


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0026_v1_7__customfields_uniqueness_1'),
    ]

    operations = [
        migrations.RunPython(fill_UUIDs),
        migrations.RunPython(rename_cfields_with_same_same),
    ]
