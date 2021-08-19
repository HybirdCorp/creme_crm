# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
################################################################################

import logging
from functools import partial

from django.apps import apps
from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _

from creme.creme_core import bricks as core_bricks
from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.core.entity_filter import condition_handler, operators
from creme.creme_core.forms import LAYOUT_DUAL_FIRST, LAYOUT_DUAL_SECOND
from creme.creme_core.gui.custom_form import EntityCellCustomFormSpecial
from creme.creme_core.gui.menu import ContainerEntry
from creme.creme_core.management.commands.creme_populate import BasePopulator
from creme.creme_core.models import (
    BrickDetailviewLocation,
    CustomFormConfigItem,
    EntityFilter,
    HeaderFilter,
    MenuConfigItem,
    RelationType,
    SearchConfigItem,
)
from creme.creme_core.utils import create_if_needed

from . import (
    bricks,
    constants,
    custom_forms,
    folder_model_is_custom,
    get_document_model,
    get_folder_model,
    menu,
)
from .models import DocumentCategory, FolderCategory

logger = logging.getLogger(__name__)


class Populator(BasePopulator):
    dependencies = ['creme_core']

    def populate(self):
        already_populated = RelationType.objects.filter(
            pk=constants.REL_SUB_RELATED_2_DOC,
        ).exists()

        Document = get_document_model()
        Folder   = get_folder_model()

        RelationType.objects.smart_update_or_create(
            (constants.REL_SUB_RELATED_2_DOC, _('related to the document')),
            (constants.REL_OBJ_RELATED_2_DOC, _('document related to'),      [Document])
        )

        # ---------------------------
        # TODO: pk string (or UUID) (+ move DOCUMENTS_FROM_EMAILS in 'emails' app) ??
        entities_cat = create_if_needed(
            FolderCategory,
            {'pk': constants.DOCUMENTS_FROM_ENTITIES},
            name=str(constants.DOCUMENTS_FROM_ENTITIES_NAME), is_custom=False,
        )
        create_if_needed(
            FolderCategory,
            {'pk': constants.DOCUMENTS_FROM_EMAILS},
            name=str(constants.DOCUMENTS_FROM_EMAILS_NAME), is_custom=False,
        )

        # TODO: created by 'products' & 'persons' app ?
        create_doc_cat = DocumentCategory.objects.get_or_create
        create_doc_cat(
            uuid=constants.UUID_DOC_CAT_IMG_PRODUCT,
            defaults={
                'name': _('Product image'),
                'is_custom': False,
            },
        )
        create_doc_cat(
            uuid=constants.UUID_DOC_CAT_IMG_ORGA,
            defaults={
                'name': _('Organisation logo'),
                'is_custom': False,
            },
        )
        create_doc_cat(
            uuid=constants.UUID_DOC_CAT_IMG_CONTACT,
            defaults={
                'name': _('Contact photograph'),
                'is_custom': False,
            },
        )

        # ---------------------------
        user = get_user_model().objects.get_admin()

        if not folder_model_is_custom():
            get_create_folder = Folder.objects.get_or_create
            get_create_folder(
                uuid=constants.UUID_FOLDER_RELATED2ENTITIES,
                defaults={
                    'user':        user,
                    'title':       'Creme',
                    'category':    entities_cat,
                    'description': _('Folder containing all the documents related to entities'),
                },
            )
            get_create_folder(
                uuid=constants.UUID_FOLDER_IMAGES,
                defaults={
                    'user':  user,
                    'title': _('Images'),
                }
            )

        # ---------------------------
        create_hf = HeaderFilter.objects.create_if_needed
        create_hf(
            pk=constants.DEFAULT_HFILTER_DOCUMENT, model=Document,
            name=_('Document view'),
            cells_desc=[
                (EntityCellRegularField, {'name': 'title'}),
                (EntityCellRegularField, {'name': 'linked_folder__title'}),
                (EntityCellRegularField, {'name': 'mime_type'}),
            ],
        )
        create_hf(
            pk=constants.DEFAULT_HFILTER_FOLDER, model=Folder,
            name=_('Folder view'),
            cells_desc=[
                (EntityCellRegularField, {'name': 'title'}),
                (EntityCellRegularField, {'name': 'description'}),
                (EntityCellRegularField, {'name': 'category'}),
            ],
        )

        # ---------------------------
        EntityFilter.objects.smart_update_or_create(
            constants.EFILTER_IMAGES, name=_('Images'), model=Document,
            is_custom=False, user='admin',
            conditions=[
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=Document,
                    operator=operators.StartsWithOperator,
                    field_name='mime_type__name',
                    values=[constants.MIMETYPE_PREFIX_IMG],
                ),
            ],
        )

        # ---------------------------
        common_groups_desc = [
            {
                'name': _('Description'),
                'layout': LAYOUT_DUAL_SECOND,
                'cells': [
                    (EntityCellRegularField, {'name': 'description'}),
                ],
            }, {
                'name': _('Custom fields'),
                'layout': LAYOUT_DUAL_SECOND,
                'cells': [
                    (
                        EntityCellCustomFormSpecial,
                        {'name': EntityCellCustomFormSpecial.REMAINING_CUSTOMFIELDS},
                    ),
                ],
            },
        ]
        creation_only_groups_desc = [
            {
                'name': _('Properties'),
                'cells': [
                    (
                        EntityCellCustomFormSpecial,
                        {'name': EntityCellCustomFormSpecial.CREME_PROPERTIES},
                    ),
                ],
            }, {
                'name': _('Relationships'),
                'cells': [
                    (
                        EntityCellCustomFormSpecial,
                        {'name': EntityCellCustomFormSpecial.RELATIONS},
                    ),
                ],
            },
        ]
        base_folder_groups_desc = [
            {
                'name': _('General information'),
                'layout': LAYOUT_DUAL_FIRST,
                'cells': [
                    (EntityCellRegularField, {'name': 'user'}),
                    (EntityCellRegularField, {'name': 'title'}),
                    (EntityCellRegularField, {'name': 'parent_folder'}),
                    (EntityCellRegularField, {'name': 'category'}),
                    (
                        EntityCellCustomFormSpecial,
                        {'name': EntityCellCustomFormSpecial.REMAINING_REGULARFIELDS},
                    ),
                ],
            },
            *common_groups_desc,
        ]

        CustomFormConfigItem.objects.create_if_needed(
            descriptor=custom_forms.FOLDER_CREATION_CFORM,
            groups_desc=[
                *base_folder_groups_desc,
                *creation_only_groups_desc,
            ],
        )
        CustomFormConfigItem.objects.create_if_needed(
            descriptor=custom_forms.FOLDER_EDITION_CFORM,
            groups_desc=base_folder_groups_desc,
        )

        CustomFormConfigItem.objects.create_if_needed(
            descriptor=custom_forms.DOCUMENT_CREATION_CFORM,
            groups_desc=[
                {
                    'name': _('General information'),
                    'layout': LAYOUT_DUAL_FIRST,
                    'cells': [
                        (EntityCellRegularField, {'name': 'user'}),
                        (EntityCellRegularField, {'name': 'title'}),
                        (EntityCellRegularField, {'name': 'filedata'}),
                        (EntityCellRegularField, {'name': 'linked_folder'}),
                        (EntityCellRegularField, {'name': 'categories'}),
                        (
                            EntityCellCustomFormSpecial,
                            {'name': EntityCellCustomFormSpecial.REMAINING_REGULARFIELDS},
                        ),
                    ],
                },
                *common_groups_desc,
                *creation_only_groups_desc,
            ],
        )
        CustomFormConfigItem.objects.create_if_needed(
            descriptor=custom_forms.DOCUMENT_EDITION_CFORM,
            groups_desc=[
                {
                    'name': _('General information'),
                    'layout': LAYOUT_DUAL_FIRST,
                    'cells': [
                        (EntityCellRegularField, {'name': 'user'}),
                        (EntityCellRegularField, {'name': 'title'}),
                        (EntityCellRegularField, {'name': 'linked_folder'}),
                        (EntityCellRegularField, {'name': 'categories'}),
                        (
                            EntityCellCustomFormSpecial,
                            {'name': EntityCellCustomFormSpecial.REMAINING_REGULARFIELDS},
                        ),
                    ],
                },
                *common_groups_desc,
            ],
        )

        # ---------------------------
        create_sci = SearchConfigItem.objects.create_if_needed
        create_sci(Document, ['title', 'description', 'linked_folder__title', 'categories__name'])
        create_sci(Folder,   ['title', 'description', 'category__name'])

        # ---------------------------
        # TODO: move to "not already_populated" section in creme2.4
        if not MenuConfigItem.objects.filter(entry_id__startswith='documents-').exists():
            container = MenuConfigItem.objects.get_or_create(
                entry_id=ContainerEntry.id,
                entry_data={'label': _('Tools')},
                defaults={'order': 100},
            )[0]

            create_mitem = partial(MenuConfigItem.objects.create, parent=container)
            create_mitem(entry_id=menu.DocumentsEntry.id, order=10)
            create_mitem(entry_id=menu.FoldersEntry.id,   order=20)

        # ---------------------------
        if not already_populated:
            RIGHT = BrickDetailviewLocation.RIGHT

            BrickDetailviewLocation.objects.multi_create(
                defaults={'model': Folder, 'zone': BrickDetailviewLocation.LEFT},
                data=[
                    {'order': 5},  # generic info brick
                    {'brick': core_bricks.CustomFieldsBrick, 'order': 40},
                    {'brick': bricks.ChildFoldersBrick,      'order': 50},
                    {'brick': bricks.FolderDocsBrick,        'order': 60},
                    {'brick': core_bricks.PropertiesBrick,   'order': 450},
                    {'brick': core_bricks.RelationsBrick,    'order': 500},

                    {'brick': core_bricks.HistoryBrick, 'order': 20, 'zone': RIGHT},
                ],
            )

            if apps.is_installed('creme.assistants'):
                logger.info(
                    'Assistants app is installed'
                    ' => we use the assistants blocks on detail view'
                )

                from creme.assistants import bricks as a_bricks

                BrickDetailviewLocation.objects.multi_create(
                    defaults={'zone': RIGHT},
                    data=[
                        {'brick': a_bricks.TodosBrick,        'order': 100},
                        {'brick': a_bricks.MemosBrick,        'order': 200},
                        {'brick': a_bricks.AlertsBrick,       'order': 300},
                        {'brick': a_bricks.UserMessagesBrick, 'order': 400},
                    ],
                )
