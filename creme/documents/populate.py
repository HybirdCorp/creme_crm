# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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
from django.contrib.contenttypes.models import ContentType

from creme_core.models.header_filter import HeaderFilterItem, HeaderFilter, HFI_FIELD
from creme_core.models.relation import create_relation_type
from creme_core.models import BlockConfigItem
from creme_core.utils import create_or_update_models_instance as create
from creme_core.management.commands.creme_populate import BasePopulator

from documents.models import Document, FolderCategory, Folder
from documents.blocks import linked_docs_block
from documents.constants import *


class Populator(BasePopulator):
    dependencies = ['creme.core']

    def populate(self, *args, **kwargs):
        create_relation_type((REL_SUB_RELATED_2_DOC, u'concerne le document'),
                             (REL_OBJ_RELATED_2_DOC, u'document concerné par',       [Document]))
        create_relation_type((REL_SUB_CURRENT_DOC,   u'est le document courant de'), #used for several types of document, not only documents.Document
                             (REL_OBJ_CURRENT_DOC,   u'a comme document courant'))

        category = create(FolderCategory, name=_(u"Documents crées à partir des fiches"))

        create(Folder, title="Creme", description=_(u"Classeur contenant tous les documents créés à partir des fiches"), category_id=category.pk, user_id=1)

        hf_id = create(HeaderFilter, 'documents-hf', name=u'Vue de Document', entity_type_id=ContentType.objects.get_for_model(Document).id, is_custom=False).id
        pref  = 'documents-hfi_'
        create(HeaderFilterItem, pref + 'title',  order=1, name='title',  title=_(u'Titre'),    type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, sortable=True, filter_string="title__icontains")
        create(HeaderFilterItem, pref + 'folder', order=2, name='folder', title=_(u'Classeur'), type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, sortable=True, filter_string="folder__title__icontains")

        create(BlockConfigItem, 'documents-linked_docs_block', content_type=None, block_id=linked_docs_block.id_, order=1000, on_portal=False)
