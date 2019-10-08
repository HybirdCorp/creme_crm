# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2019  Hybird
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

from functools import partial
import logging

from django.apps import apps
from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _

from creme.creme_core import bricks as core_bricks
from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.core.entity_filter import condition_handler, operators
from creme.creme_core.management.commands.creme_populate import BasePopulator
from creme.creme_core.models import (
    RelationType,
    BrickDetailviewLocation,
    SearchConfigItem,
    HeaderFilter,
    EntityFilter,
)  # EntityFilterCondition
from creme.creme_core.utils import create_if_needed

from . import (
    get_document_model, get_folder_model,
    folder_model_is_custom,
    constants,
    bricks,
)
from .models import FolderCategory, DocumentCategory

logger = logging.getLogger(__name__)


class Populator(BasePopulator):
    dependencies = ['creme_core']

    def populate(self):
        already_populated = RelationType.objects.filter(pk=constants.REL_SUB_RELATED_2_DOC).exists()

        Document = get_document_model()
        Folder   = get_folder_model()

        RelationType.create(
            (constants.REL_SUB_RELATED_2_DOC, _('related to the document')),
            (constants.REL_OBJ_RELATED_2_DOC, _('document related to'),      [Document])
        )

        # ---------------------------
        # TODO: pk string (or UUID) (+ move DOCUMENTS_FROM_EMAILS in 'emails' app) ??
        entities_cat = create_if_needed(FolderCategory, {'pk': constants.DOCUMENTS_FROM_ENTITIES}, name=str(constants.DOCUMENTS_FROM_ENTITIES_NAME), is_custom=False)
        create_if_needed(FolderCategory,                {'pk': constants.DOCUMENTS_FROM_EMAILS},   name=str(constants.DOCUMENTS_FROM_EMAILS_NAME),   is_custom=False)

        # TODO: created by 'products' & 'persons' app ?
        create_doc_cat = DocumentCategory.objects.get_or_create
        create_doc_cat(uuid=constants.UUID_DOC_CAT_IMG_PRODUCT,
                       defaults={'name': _('Product image'),
                                 'is_custom': False,
                                }
                      )
        create_doc_cat(uuid=constants.UUID_DOC_CAT_IMG_ORGA,
                       defaults={'name': _('Organisation logo'),
                                 'is_custom': False,
                                }
                      )
        create_doc_cat(uuid=constants.UUID_DOC_CAT_IMG_CONTACT,
                       defaults={'name': _('Contact photograph'),
                                 'is_custom': False,
                                }
                      )

        # ---------------------------
        user_qs = get_user_model().objects.order_by('id')
        user = user_qs.filter(is_superuser=True, is_staff=False).first() or \
               user_qs.filter(is_superuser=True).first() or \
               user_qs[0]

        if not folder_model_is_custom():
            get_create_folder = Folder.objects.get_or_create
            get_create_folder(uuid=constants.UUID_FOLDER_RELATED2ENTITIES,
                              defaults={
                                  'user':        user,
                                  'title':       'Creme',
                                  'category':    entities_cat,
                                  'description': _('Folder containing all the documents related to entities'),
                              }
                             )
            get_create_folder(uuid=constants.UUID_FOLDER_IMAGES,
                              defaults={
                                  'user':  user,
                                  'title': _('Images'),
                              }
                             )

        # ---------------------------
        HeaderFilter.create(pk=constants.DEFAULT_HFILTER_DOCUMENT, model=Document,
                            name=_('Document view'),
                            cells_desc=[(EntityCellRegularField, {'name': 'title'}),
                                        (EntityCellRegularField, {'name': 'linked_folder__title'}),
                                        (EntityCellRegularField, {'name': 'mime_type'}),
                                       ]
                                )
        HeaderFilter.create(pk=constants.DEFAULT_HFILTER_FOLDER, model=Folder,
                            name=_('Folder view'),
                            cells_desc=[(EntityCellRegularField, {'name': 'title'}),
                                        (EntityCellRegularField, {'name': 'description'}),
                                        (EntityCellRegularField, {'name': 'category'}),
                                       ]
                           )

        # ---------------------------
        EntityFilter.create(
            constants.EFILTER_IMAGES, name=_('Images'), model=Document,
            is_custom=False, user='admin',
            conditions=[
                # EntityFilterCondition.build_4_field(
                #     model=Document,
                #     operator=EntityFilterCondition.STARTSWITH,
                #     name='mime_type__name',
                #     values=[constants.MIMETYPE_PREFIX_IMG],
                # ),
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=Document,
                    operator=operators.StartsWithOperator,
                    field_name='mime_type__name',
                    values=[constants.MIMETYPE_PREFIX_IMG],
                ),
            ],
        )

        # ---------------------------
        create_sci = SearchConfigItem.create_if_needed
        create_sci(Document, ['title', 'description', 'linked_folder__title', 'categories__name'])
        create_sci(Folder,   ['title', 'description', 'category__name'])

        # ---------------------------
        if not already_populated:
            LEFT = BrickDetailviewLocation.LEFT
            RIGHT = BrickDetailviewLocation.RIGHT
            create_bdl = partial(BrickDetailviewLocation.objects.create_if_needed, model=Folder)

            BrickDetailviewLocation.objects.create_for_model_brick(order=5, zone=LEFT, model=Folder)
            create_bdl(brick=core_bricks.CustomFieldsBrick, order=40,  zone=LEFT)
            create_bdl(brick=bricks.ChildFoldersBrick,      order=50,  zone=LEFT)
            create_bdl(brick=bricks.FolderDocsBrick,        order=60,  zone=LEFT)
            create_bdl(brick=core_bricks.PropertiesBrick,   order=450, zone=LEFT)
            create_bdl(brick=core_bricks.RelationsBrick,    order=500, zone=LEFT)
            create_bdl(brick=core_bricks.HistoryBrick,      order=20,  zone=RIGHT)

            if apps.is_installed('creme.assistants'):
                logger.info('Assistants app is installed => we use the assistants blocks on detail view')

                from creme.assistants import bricks as a_bricks

                create_bdl(brick=a_bricks.TodosBrick,        order=100, zone=RIGHT)
                create_bdl(brick=a_bricks.MemosBrick,        order=200, zone=RIGHT)
                create_bdl(brick=a_bricks.AlertsBrick,       order=300, zone=RIGHT)
                create_bdl(brick=a_bricks.UserMessagesBrick, order=400, zone=RIGHT)
