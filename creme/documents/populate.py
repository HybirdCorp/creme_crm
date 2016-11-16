# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2016  Hybird
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

from django.apps import apps
from django.contrib.auth import get_user_model
from django.utils.translation import ugettext as _

from creme.creme_core.blocks import (properties_block, relations_block,
        customfields_block, history_block)
from creme.creme_core.buttons import merge_entities_button
from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.management.commands.creme_populate import BasePopulator
from creme.creme_core.models import (RelationType, BlockDetailviewLocation,
        SearchConfigItem, HeaderFilter, EntityFilter, EntityFilterCondition, ButtonMenuItem)
from creme.creme_core.utils import create_if_needed

from . import get_document_model, get_folder_model, folder_model_is_custom
from . import constants
from .blocks import folder_docs_block, child_folders_block
from .models import FolderCategory, DocumentCategory


logger = logging.getLogger(__name__)


class Populator(BasePopulator):
    dependencies = ['creme_core']

    def populate(self):
        already_populated = RelationType.objects.filter(pk=constants.REL_SUB_RELATED_2_DOC).exists()

        Document = get_document_model()
        Folder   = get_folder_model()

        RelationType.create((constants.REL_SUB_RELATED_2_DOC, _(u'related to the document')),
                            (constants.REL_OBJ_RELATED_2_DOC, _(u'document related to'),      [Document])
                           )

        # ---------------------------
        # TODO: pk string (+ move DOCUMENTS_FROM_EMAILS in 'emails' app) ??
        entities_cat = create_if_needed(FolderCategory, {'pk': constants.DOCUMENTS_FROM_ENTITIES}, name=unicode(constants.DOCUMENTS_FROM_ENTITIES_NAME), is_custom=False)
        create_if_needed(FolderCategory,                {'pk': constants.DOCUMENTS_FROM_EMAILS},   name=unicode(constants.DOCUMENTS_FROM_EMAILS_NAME),   is_custom=False)

        # TODO: created by 'products' & 'persons' app ?
        create_doc_cat = DocumentCategory.objects.get_or_create
        create_doc_cat(uuid=constants.UUID_DOC_CAT_IMG_PRODUCT,
                       defaults={'name': _(u'Product image'),
                                 'is_custom': False,
                                }
                      )
        create_doc_cat(uuid=constants.UUID_DOC_CAT_IMG_ORGA,
                       defaults={'name': _(u'Organisation logo'),
                                 'is_custom': False,
                                }
                      )
        create_doc_cat(uuid=constants.UUID_DOC_CAT_IMG_CONTACT,
                       defaults={'name': _(u'Contact photograph'),
                                 'is_custom': False,
                                }
                      )

        # ---------------------------
        user_qs = get_user_model().objects.order_by('id')
        user = user_qs.filter(is_superuser=True, is_staff=False).first() or \
               user_qs.filter(is_superuser=True).first() or \
               user_qs[0]

        if not folder_model_is_custom():
            if not Folder.objects.filter(title='Creme').exists():  # TODO: UUID ??
                # Folder.objects.create(user=get_user_model().objects.get(pk=1),
                Folder.objects.create(user=user,
                                      title='Creme', category=entities_cat,
                                      description=_(u'Folder containing all the documents related to entities'),
                                     )
            else:
                logger.info("A Folder with title 'Creme' already exists => no re-creation")

        # ---------------------------
        HeaderFilter.create(pk=constants.DEFAULT_HFILTER_DOCUMENT, model=Document,
                            name=_(u'Document view'),
                            cells_desc=[(EntityCellRegularField, {'name': 'title'}),
                                        (EntityCellRegularField, {'name': 'folder__title'}),
                                        (EntityCellRegularField, {'name': 'mime_type'}),
                                       ]
                                )
        HeaderFilter.create(pk=constants.DEFAULT_HFILTER_FOLDER, model=Folder,
                            name=_(u'Folder view'),
                            cells_desc=[(EntityCellRegularField, {'name': 'title'}),
                                        (EntityCellRegularField, {'name': 'description'}),
                                        (EntityCellRegularField, {'name': 'category'}),
                                       ]
                           )

        # ---------------------------
        EntityFilter.create(constants.EFILTER_IMAGES, name=_(u'Images'), model=Document,
                            is_custom=False, user='admin',
                            conditions=[EntityFilterCondition.build_4_field(model=Document,
                                              operator=EntityFilterCondition.STARTSWITH,
                                              name='mime_type__name',
                                              values=[constants.MIMETYPE_PREFIX_IMG],
                                          ),
                                       ],
                           )

        # ---------------------------
        create_sci = SearchConfigItem.create_if_needed
        create_sci(Document, ['title', 'description', 'folder__title', 'categories__name'])
        create_sci(Folder,   ['title', 'description', 'category__name'])

        # ---------------------------
        if not already_populated:
            if not folder_model_is_custom():
                Folder.objects.create(user=user, title=_(u'Images'))  # TODO: UUID ??

            LEFT = BlockDetailviewLocation.LEFT
            RIGHT = BlockDetailviewLocation.RIGHT
            create_bdl = BlockDetailviewLocation.create

            BlockDetailviewLocation.create_4_model_block(order=5, zone=LEFT, model=Folder)
            create_bdl(block_id=customfields_block.id_,  order=40,  zone=LEFT,  model=Folder)
            create_bdl(block_id=child_folders_block.id_, order=50,  zone=LEFT,  model=Folder)
            create_bdl(block_id=folder_docs_block.id_,   order=60,  zone=LEFT,  model=Folder)
            create_bdl(block_id=properties_block.id_,    order=450, zone=LEFT,  model=Folder)
            create_bdl(block_id=relations_block.id_,     order=500, zone=LEFT,  model=Folder)
            create_bdl(block_id=history_block.id_,       order=20,  zone=RIGHT, model=Folder)

            ButtonMenuItem.create_if_needed(pk='document-merge_folders_button', model=Folder, button=merge_entities_button,  order=100)

            if apps.is_installed('creme.assistants'):
                logger.info('Assistants app is installed => we use the assistants blocks on detail view')

                from creme.assistants.blocks import alerts_block, memos_block, todos_block, messages_block

                create_bdl(block_id=todos_block.id_,    order=100, zone=RIGHT, model=Folder)
                create_bdl(block_id=memos_block.id_,    order=200, zone=RIGHT, model=Folder)
                create_bdl(block_id=alerts_block.id_,   order=300, zone=RIGHT, model=Folder)
                create_bdl(block_id=messages_block.id_, order=400, zone=RIGHT, model=Folder)
