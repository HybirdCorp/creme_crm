# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

from json import dumps as json_dump

# from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.models import Relation
from creme.creme_core.gui.bricks import SimpleBrick, QuerysetBrick, EntityBrick

from creme import documents
from .constants import REL_SUB_RELATED_2_DOC


Folder   = documents.get_folder_model()
Document = documents.get_document_model()


class DocumentBarHatBrick(SimpleBrick):
    # NB: we do not set an ID because it's the main Header Brick.
    template_name = 'documents/bricks/document-hat-bar.html'


class DocumentBrick(EntityBrick):
    verbose_name = _(u'Information on the document')

    def _get_cells(self, entity, context):
        cells = super(DocumentBrick, self)._get_cells(entity=entity, context=context)
        cells.append(EntityCellRegularField.build(model=Document, name='categories'))

        return cells

    def _get_title(self, entity, context):
        return self.verbose_name


class FolderDocsBrick(QuerysetBrick):
    id_           = QuerysetBrick.generate_id('documents', 'folder_docs')
    dependencies  = (Document,)
    verbose_name  = _(u'Folder documents')
    template_name = 'documents/bricks/documents.html'
    target_ctypes = (Folder,)
    order_by      = 'title'

    def detailview_display(self, context):
        folder_id = context['object'].id
        # q_dict = {'folder': folder_id}
        q_dict = {'linked_folder': folder_id}
        return self._render(self.get_template_context(
                    context,
                    Document.objects.filter(**q_dict),
                    # Document.objects.filter(is_deleted=False, **q_dict), TODO: problem deleted docs avoid folder deletion...
                    # ct_id=ContentType.objects.get_for_model(Document).id,
                    q_filter=json_dump(q_dict),
        ))


class ChildFoldersBrick(QuerysetBrick):
    id_           = QuerysetBrick.generate_id('documents', 'child_folders')
    dependencies  = (Folder,)
    order_by      = 'title'
    verbose_name  = _(u'Child Folders')
    template_name = 'documents/bricks/child-folders.html'
    target_ctypes = (Folder,)

    def detailview_display(self, context):
        folder = context['object']

        return self._render(self.get_template_context(
                    context,
                    Folder.objects.filter(parent_folder=folder),
                    folder_model=Folder,
        ))


class LinkedDocsBrick(QuerysetBrick):
    id_           = QuerysetBrick.generate_id('documents', 'linked_docs')
    dependencies  = (Relation, Document)
    relation_type_deps = (REL_SUB_RELATED_2_DOC, )
    verbose_name  = _(u'Linked documents')
    template_name = 'documents/bricks/linked-docs.html'
    order_by      = 'id'  # For consistent ordering between 2 queries (for pages)

    def detailview_display(self, context):
        entity = context['object']
        btc = self.get_template_context(
                    context,
                    Document.get_linkeddoc_relations(entity),
                    predicate_id=REL_SUB_RELATED_2_DOC,
                    # ct_doc=ContentType.objects.get_for_model(Document),
        )
        relations = btc['page'].object_list
        # docs = {c.id: c
        #             for c in Document.objects.filter(pk__in=[r.object_entity_id for r in relations])
        #                                      .select_related('folder')
        #        }
        docs = Document.objects.filter(pk__in=[r.object_entity_id for r in relations]) \
                               .select_related('linked_folder') \
                               .in_bulk()

        for relation in relations:
            relation.object_entity = docs[relation.object_entity_id]

        return self._render(btc)
