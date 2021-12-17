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

from django.db.models.query_utils import Q
from django.utils.translation import gettext_lazy as _

from creme import documents
from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.gui.bricks import EntityBrick, QuerysetBrick, SimpleBrick
from creme.creme_core.models import Relation
from creme.creme_core.utils.queries import QSerializer

from .constants import REL_SUB_RELATED_2_DOC

Folder   = documents.get_folder_model()
Document = documents.get_document_model()


class DocumentBarHatBrick(SimpleBrick):
    # NB: we do not set an ID because it's the main Header Brick.
    template_name = 'documents/bricks/document-hat-bar.html'


class DocumentBrick(EntityBrick):
    verbose_name = _('Information on the document')

    def _get_cells(self, entity, context):
        cells = super()._get_cells(entity=entity, context=context)
        cells.append(EntityCellRegularField.build(model=Document, name='categories'))

        return cells

    def _get_title(self, entity, context):
        return self.verbose_name


class FolderDocsBrick(QuerysetBrick):
    id_ = QuerysetBrick.generate_id('documents', 'folder_docs')
    verbose_name = _('Contained documents')
    description = _(
        'Displays the documents contained by the current Folder.\n'
        'App: Documents'
    )
    dependencies = (Document,)
    template_name = 'documents/bricks/documents.html'
    target_ctypes = (Folder,)
    order_by = 'title'

    def detailview_display(self, context):
        folder_id = context['object'].id
        q_dict = {'linked_folder': folder_id}
        return self._render(self.get_template_context(
            context,
            Document.objects.filter(**q_dict),
            # TODO: problem deleted docs avoid folder deletion...
            # Document.objects.filter(is_deleted=False, **q_dict),
            q_filter=QSerializer().dumps(Q(**q_dict)),
        ))


class ChildFoldersBrick(QuerysetBrick):
    id_ = QuerysetBrick.generate_id('documents', 'child_folders')
    verbose_name = _('Child Folders')
    dependencies = (Folder,)
    order_by = 'title'
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
    id_ = QuerysetBrick.generate_id('documents', 'linked_docs')
    verbose_name = _('Linked documents')
    description = _(
        'Allows to add Documents, linked with relationships '
        '«related to the document».\n'
        'App: Documents'
    )
    dependencies = (Relation, Document)
    relation_type_deps = (REL_SUB_RELATED_2_DOC, )
    template_name = 'documents/bricks/linked-docs.html'
    order_by = 'id'  # For consistent ordering between 2 queries (for pages)

    def detailview_display(self, context):
        entity = context['object']
        rtype_id = self.relation_type_deps[0]
        btc = self.get_template_context(
            context,
            Relation.objects.filter(subject_entity=entity.id, type=rtype_id),
            predicate_id=rtype_id,
        )
        relations = btc['page'].object_list
        docs = Document.objects.filter(
            pk__in=[r.object_entity_id for r in relations],
        ).select_related('linked_folder').in_bulk()

        for relation in relations:
            relation.object_entity = docs[relation.object_entity_id]

        return self._render(btc)
