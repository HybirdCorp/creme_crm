# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2013  Hybird
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

from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext_lazy as _
from django.utils.simplejson import JSONEncoder

from creme.creme_core.models import Relation #CremeEntity
from creme.creme_core.gui.block import QuerysetBlock

from .models import Folder, Document
from .constants import REL_SUB_RELATED_2_DOC


_CT_DOC = ContentType.objects.get_for_model(Document)


class FolderDocsBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('documents', 'folder_docs')
    dependencies  = (Document,)
    verbose_name  = _(u'Folder documents')
    template_name = 'documents/templatetags/block_documents.html'
    target_ctypes = (Folder,)

    def detailview_display(self, context):
        folder_id = context['object'].id
        q_dict = {'folder':  folder_id}
        return self._render(self.get_block_template_context(
                        context,
                        Document.objects.filter(**q_dict),
                        #Document.objects.filter(is_deleted=False, **q_dict), TODO: problem deleted docs avoid folder deletion...
                        update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, folder_id),
                        ct_id=_CT_DOC.id,
                        q_filter=JSONEncoder().encode(q_dict),
                       )
                   )


class LinkedDocsBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('documents', 'linked_docs')
    dependencies  = (Relation, Document)
    relation_type_deps = (REL_SUB_RELATED_2_DOC, )
    verbose_name  = _(u'Linked documents')
    template_name = 'documents/templatetags/block_linked_docs.html'

    def detailview_display(self, context):
        entity = context['object']
        btc = self.get_block_template_context(context,
                                              Document.get_linkeddoc_relations(entity),
                                              update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, entity.id),
                                              predicate_id=REL_SUB_RELATED_2_DOC,
                                              ct_doc=_CT_DOC,
                                             )
        relations = btc['page'].object_list
        docs = dict((c.id, c) for c in Document.objects.filter(pk__in=[r.object_entity_id for r in relations])
                                                       .select_related('folder')
                   )

        for relation in relations:
            relation.object_entity = docs[relation.object_entity_id]

        return self._render(btc)


folder_docs_block = FolderDocsBlock()
linked_docs_block = LinkedDocsBlock()
