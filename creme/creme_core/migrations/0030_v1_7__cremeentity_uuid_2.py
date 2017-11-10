# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from uuid import uuid4

from django.db import migrations


def fill_UUIDs(apps, schema_editor):
    entity_mngr = apps.get_model('creme_core', 'CremeEntity').objects

    uuids = set(entity_mngr.filter(uuid__isnull=False).values_list('uuid', flat=True))

    for entity in entity_mngr.filter(uuid__isnull=True):
        # No because it updates the field 'modified'
        # entity.uuid = uuid4()
        # entity.save()

        while True:
            e_uuid = str(uuid4())

            if not e_uuid in uuids:
                uuids.add(e_uuid)
                break

        entity_mngr.filter(id=entity.id).update(uuid=e_uuid)


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0029_v1_7__cremeentity_uuid_1'),
    ]

    operations = [
        migrations.RunPython(fill_UUIDs),
    ]
