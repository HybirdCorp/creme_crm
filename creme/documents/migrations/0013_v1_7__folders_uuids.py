# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from uuid import uuid4

from django.conf import settings
from django.db import migrations
from django.utils.translation import activate as activate_trans, ugettext as _

from ..constants import UUID_FOLDER_RELATED2ENTITIES, UUID_FOLDER_IMAGES, DOCUMENTS_FROM_ENTITIES


def set_folders_UUIDs(apps, schema_editor):
    get_model = apps.get_model
    CremeEntity = get_model('creme_core', 'CremeEntity')
    Folder      = get_model('documents',  'Folder')

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

    fix_colliding_UUID(UUID_FOLDER_RELATED2ENTITIES)
    fix_colliding_UUID(UUID_FOLDER_IMAGES)

    if Folder.objects.exists():
        creme_folder = Folder.objects.filter(title='Creme', parent_folder=None, category=DOCUMENTS_FROM_ENTITIES).first()
        if creme_folder is not None:
            # update() to not change the field 'modified'
            Folder.objects.filter(id=creme_folder.id).update(uuid=UUID_FOLDER_RELATED2ENTITIES)

        activate_trans(settings.LANGUAGE_CODE)

        images_folder = Folder.objects.filter(title=_(u'Images'), parent_folder=None, category=None).first()
        if images_folder is not None:
            # idem
            Folder.objects.filter(id=images_folder.id).update(uuid=UUID_FOLDER_IMAGES)


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0030_v1_7__cremeentity_uuid_2'),
        ('documents',  '0012_v1_7__doc_categories_uniqueness'),
    ]

    run_before = [
        ('creme_core', '0031_v1_7__cremeentity_uuid_3'),
    ]

    operations = [
        migrations.RunPython(set_folders_UUIDs),
    ]
