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

from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext_lazy as _

from creme_core.gui.block import QuerysetBlock

from models import Document
from constants import REL_SUB_RELATED_2_DOC


class LinkedDocsBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('documents', 'linked_docs')
    verbose_name  = _(u'Documents liés')
    template_name = 'documents/templatetags/block_linked_docs.html'

    def __init__(self, *args, **kwargs):
        super(LinkedDocsBlock, self).__init__(*args, **kwargs)

        self._doc_ct_id = None

    def detailview_display(self, context):
        entity = context['object']

        if not self._doc_ct_id:
            self._doc_ct_id = ContentType.objects.get_for_model(Document).id

        return self._render(self.get_block_template_context(context,
                                                            Document.get_linkeddoc_relations(entity),
                                                            update_url='/documents/linked_docs/reload/%s/' % entity.id,
                                                            predicate_id=REL_SUB_RELATED_2_DOC,
                                                            ct_id=self._doc_ct_id))


linked_docs_block = LinkedDocsBlock()
