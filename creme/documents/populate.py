# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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

from logging import info

from django.utils.translation import ugettext as _
from django.contrib.auth.models import User

from creme_core.models import RelationType, BlockDetailviewLocation, SearchConfigItem, HeaderFilterItem, HeaderFilter #BlockConfigItem
from creme_core.utils import create_or_update as create
from creme_core.blocks import properties_block, relations_block, customfields_block, history_block
from creme_core.management.commands.creme_populate import BasePopulator

from documents.models import Document, FolderCategory, Folder
from documents.blocks import folder_docs_block #linked_docs_block
from documents.constants import *


class Populator(BasePopulator):
    dependencies = ['creme.creme_core']

    def populate(self, *args, **kwargs):
        RelationType.create((REL_SUB_RELATED_2_DOC, _(u'related to the document')),
                            (REL_OBJ_RELATED_2_DOC, _(u'document related to'),       [Document]))

        category_entities = create(FolderCategory, DOCUMENTS_FROM_ENTITIES, name=_(u"Documents related to entities"))
        create(FolderCategory, DOCUMENTS_FROM_EMAILS, name=_(u"Documents received by email"))

        if not Folder.objects.filter(title="Creme"):
            user = User.objects.get(pk=1)
            create(Folder, title="Creme", description=_(u"Folder containing all the documents related to entities"), category=category_entities, user=user)
        else:
            info("A Folder with title 'Creme' already exists => no re-creation")

        hf = HeaderFilter.create(pk='documents-hf_document', name=_(u"Document view"), model=Document)
        hf.set_items([HeaderFilterItem.build_4_field(model=Document, name='title'),
                      HeaderFilterItem.build_4_field(model=Document, name='folder__title'),
                     ])

        hf = HeaderFilter.create(pk='documents-hf_folder', name=_(u"Folder view"), model=Folder)
        hf.set_items([HeaderFilterItem.build_4_field(model=Folder, name='title'),
                      HeaderFilterItem.build_4_field(model=Folder, name='description'),
                      HeaderFilterItem.build_4_field(model=Folder, name='category__name'),
                     ])

        #BlockConfigItem.create(pk='documents-linked_docs_block', block_id=linked_docs_block.id_, order=1000, on_portal=False)
        BlockDetailviewLocation.create(block_id=customfields_block.id_, order=40,  zone=BlockDetailviewLocation.LEFT,  model=Folder)
        BlockDetailviewLocation.create(block_id=folder_docs_block.id_,  order=50,  zone=BlockDetailviewLocation.LEFT,  model=Folder)
        BlockDetailviewLocation.create(block_id=properties_block.id_,   order=450, zone=BlockDetailviewLocation.LEFT,  model=Folder)
        BlockDetailviewLocation.create(block_id=relations_block.id_,    order=500, zone=BlockDetailviewLocation.LEFT,  model=Folder)
        BlockDetailviewLocation.create(block_id=history_block.id_,      order=20,  zone=BlockDetailviewLocation.RIGHT, model=Folder)

        SearchConfigItem.create(Document, ['title', 'description', 'folder__title'])
        SearchConfigItem.create(Folder,   ['title', 'description', 'category__name'])
