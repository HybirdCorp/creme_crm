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
from creme_core.models import RelationType, BlockConfigItem, SearchConfigItem, SearchField
from creme_core.utils import create_or_update_models_instance as create
from creme_core.utils.meta import get_verbose_field_name
from creme_core.management.commands.creme_populate import BasePopulator

from documents.models import Document, FolderCategory, Folder
from documents.blocks import linked_docs_block
from documents.constants import *


class Populator(BasePopulator):
    dependencies = ['creme.core']

    def populate(self, *args, **kwargs):
        RelationType.create((REL_SUB_RELATED_2_DOC, _(u'related to the document')),
                            (REL_OBJ_RELATED_2_DOC, _(u'document related to'),       [Document]))
        RelationType.create((REL_SUB_CURRENT_DOC,   _(u'is the current document of')), #used for several types of document, not only documents.Document
                            (REL_OBJ_CURRENT_DOC,   _(u'has as current document')))

        category = create(FolderCategory, DOCUMENTS_FROM_ENTITIES, name=_(u"Documents related to entities"))

        create(Folder, title="Creme", description=_(u"Folder containing all the documents related to entities"), category_id=category.pk, user_id=1)

        hf_id = create(HeaderFilter, 'documents-hf', name=_(u'Document view'), entity_type_id=ContentType.objects.get_for_model(Document).id, is_custom=False).id
        pref  = 'documents-hfi_'
        create(HeaderFilterItem, pref + 'title',  order=1, name='title',  title=_(u'Title'),  type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, sortable=True, filter_string="title__icontains")
        create(HeaderFilterItem, pref + 'folder', order=2, name='folder', title=_(u'Folder'), type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, sortable=True, filter_string="folder__title__icontains")

        create(BlockConfigItem, 'documents-linked_docs_block', content_type=None, block_id=linked_docs_block.id_, order=1000, on_portal=False)

        model = Document
        sci = create(SearchConfigItem, content_type_id=ContentType.objects.get_for_model(model).id)
        SCI_pk = sci.pk
        sci_fields = ['title', 'description', 'folder__title']
        for i, field in enumerate(sci_fields):
            create(SearchField, field=field, field_verbose_name=get_verbose_field_name(model, field), order=i, search_config_item_id=SCI_pk)

        model = Folder
        sci = create(SearchConfigItem, content_type_id=ContentType.objects.get_for_model(model).id)
        SCI_pk = sci.pk
        sci_fields = ['title', 'description', 'category__name']
        for i, field in enumerate(sci_fields):
            create(SearchField, field=field, field_verbose_name=get_verbose_field_name(model, field), order=i, search_config_item_id=SCI_pk)
