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

from django.utils.translation import ugettext as _

from creme_core.models.header_filter import HeaderFilterItem, HeaderFilter, HFI_FIELD
from creme_core.models import RelationType, BlockConfigItem, SearchConfigItem
from creme_core.utils import create_or_update as create
from creme_core.management.commands.creme_populate import BasePopulator

from documents.models import Document, FolderCategory, Folder
from documents.blocks import linked_docs_block
from documents.constants import *


class Populator(BasePopulator):
    dependencies = ['creme.creme_core']

    def populate(self, *args, **kwargs):
        RelationType.create((REL_SUB_RELATED_2_DOC, _(u'related to the document')),
                            (REL_OBJ_RELATED_2_DOC, _(u'document related to'),       [Document]))
        RelationType.create((REL_SUB_CURRENT_DOC,   _(u'is the current document of')), #used for several types of document, not only documents.Document
                            (REL_OBJ_CURRENT_DOC,   _(u'has as current document')))

        category_entities = create(FolderCategory, DOCUMENTS_FROM_ENTITIES, name=_(u"Documents related to entities"))
        create(FolderCategory, DOCUMENTS_FROM_EMAILS, name=_(u"Documents received by email"))

        create(Folder, title="Creme", description=_(u"Folder containing all the documents related to entities"), category=category_entities, user_id=1)

        hf   = HeaderFilter.create(pk='documents-hf', name=_(u"Document view"), model=Document)
        pref = 'documents-hfi_'
        create(HeaderFilterItem, pref + 'title',  order=1, name='title',         title=_(u'Title'),          type=HFI_FIELD, header_filter=hf, has_a_filter=True, editable=True, sortable=True, filter_string="title__icontains")
        create(HeaderFilterItem, pref + 'folder', order=2, name='folder__title', title=_(u'Folder - Title'), type=HFI_FIELD, header_filter=hf, has_a_filter=True, editable=True, sortable=True, filter_string="folder__title__icontains")

        create(BlockConfigItem, 'documents-linked_docs_block', content_type=None, block_id=linked_docs_block.id_, order=1000, on_portal=False)

        SearchConfigItem.create(Document, ['title', 'description', 'folder__title'])
        SearchConfigItem.create(Folder,   ['title', 'description', 'category__name'])
