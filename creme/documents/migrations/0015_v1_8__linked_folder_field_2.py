# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from json import loads as json_load, dumps as json_dump

from django.conf import settings
from django.db import migrations

EFC_FIELD = 5


def rename_linkedfolder_fields(apps, schema_editor):
    if settings.DOCUMENTS_DOCUMENT_MODEL != 'documents.Document':
        return

    get_model = apps.get_model

    ct = get_model('contenttypes', 'ContentType').objects.filter(app_label='documents', model='document').first()
    if ct is None:
        return

    ct_id = ct.id

    # HeaderFilter -----------------
    for hfilter in get_model('creme_core', 'HeaderFilter').objects.filter(entity_type_id=ct_id)\
                                                                  .exclude(json_cells=None):
        # [{"type": "regular_field", "value": "title"},
        #  {"type": "regular_field", "value": "folder"},    # <====
        #  {"type": "regular_field", "value": "filedata"},
        #  {"type": "relation", "value": "documents-object_related_2_doc"}
        # ]
        cells_data = json_load(hfilter.json_cells)
        save = False

        for cell_data in cells_data:
            if cell_data.get('type') == 'regular_field' and cell_data.get('value', '').startswith('folder'):
                cell_data['value'] = cell_data['value'].replace('folder', 'linked_folder')
                save = True

        if save:
            hfilter.json_cells = json_dump(cells_data)
            hfilter.save()

    # CustomBlockConfigItem -------------
    for cbci in get_model('creme_core', 'CustomBlockConfigItem').objects.filter(content_type_id=ct_id) \
                                                                        .exclude(json_cells=None):
        cells_data = json_load(cbci.json_cells)
        save = False

        for cell_data in cells_data:
            if cell_data.get('type') == 'regular_field' and cell_data.get('value', '').startswith('folder'):
                cell_data['value'] = cell_data['value'].replace('folder', 'linked_folder')
                save = True

        if save:
            cbci.json_cells = json_dump(cells_data)
            cbci.save()

    # RelationBlockItem ---------------
    for rbci in get_model('creme_core', 'RelationBlockItem').objects.all():
        # {"66": [{"type": "regular_field", "value": "last_name"},
        #         {"type": "regular_field", "value": "first_name"},
        #         {"type": "regular_field", "value": "email"},
        #        ],
        #  "62": [...]
        #   ...
        # }
        cells_map_data = json_load(rbci.json_cells_map)
        save = False

        for cells_ctid, cells_data in cells_map_data.iteritems():
            if int(cells_ctid) == ct_id:
                for cell_data in cells_data:
                    if cell_data.get('type') == 'regular_field' and cell_data.get('value', '').startswith('folder'):
                        cell_data['value'] = cell_data['value'].replace('folder', 'linked_folder')
                        save = True

                if save:
                    rbci.json_cells_map = json_dump(cells_map_data)
                    rbci.save()
                    break

    # EntityFilter -------------------
    old_prefix = 'folder__'
    new_prefix = 'linked_folder__'

    for cond in get_model('creme_core', 'EntityFilterCondition').objects.filter(filter__entity_type_id=ct_id,
                                                                                type=EFC_FIELD,
                                                                                name__startswith='folder',
                                                                               ):
        if cond.name == 'folder':
            cond.name = 'linked_folder'
            cond.save()
        elif cond.name.startswith(old_prefix):
            cond.name = new_prefix + cond.name[len(old_prefix):]
            cond.save()


class Migration(migrations.Migration):
    dependencies = [
        ('documents', '0014_v1_8__linked_folder_field_1'),
    ]

    operations = [
        migrations.RunPython(rename_linkedfolder_fields),
    ]
