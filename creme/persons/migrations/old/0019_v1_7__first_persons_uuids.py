# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from uuid import uuid4

from django.conf import settings
from django.db import migrations

from ..constants import UUID_FIRST_CONTACT, UUID_FIRST_ORGA


def fix_colliding_UUIDs(apps, schema_editor):
    CremeEntity = apps.get_model('creme_core', 'CremeEntity')

    def fix_colliding_UUID(protected_uuid):
        colliding_entitity = CremeEntity.objects.filter(uuid=protected_uuid).first()

        if colliding_entitity:
            while True:
                e_uuid = str(uuid4())
                if e_uuid == protected_uuid:
                    continue

                if not CremeEntity.objects.filter(uuid=e_uuid).exists():
                    CremeEntity.objects.filter(id=colliding_entitity).update(uuid=e_uuid)
                    break

    fix_colliding_UUID(UUID_FIRST_ORGA)
    fix_colliding_UUID(UUID_FIRST_CONTACT)


def set_first_managed_orga_UUID(apps, schema_editor):
    if settings.PERSONS_ORGANISATION_MODEL == 'persons.Organisation':
        orga_mngr = apps.get_model('persons', 'Organisation').objects
        orga = orga_mngr.filter(is_managed=True).order_by('id').first()

        if orga is not None:
            # update() to not change the field 'modified'
            orga_mngr.filter(id=orga.id).update(uuid=UUID_FIRST_ORGA)


def set_admin_contact_UUID(apps, schema_editor):
    if settings.PERSONS_CONTACT_MODEL == 'persons.Contact':
        contact_mngr = apps.get_model('persons', 'Contact').objects
        contact = contact_mngr.filter(is_user__is_superuser=True).order_by('id').first()

        if contact is not None:
            contact_mngr.filter(id=contact.id).update(uuid=UUID_FIRST_CONTACT)


class Migration(migrations.Migration):
    dependencies = [
        ('persons', '0018_v1_7__organisation_managed_2'),
    ]

    operations = [
        migrations.RunPython(fix_colliding_UUIDs),
        migrations.RunPython(set_first_managed_orga_UUID),
        migrations.RunPython(set_admin_contact_UUID),
    ]
