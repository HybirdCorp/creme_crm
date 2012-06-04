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

from django.utils.translation import ugettext_lazy as _

from creme_core.registry import creme_registry
from creme_core.gui import creme_menu, block_registry, icon_registry, bulk_update_registry, quickforms_registry

from documents.models import Document, Folder
from documents.blocks import folder_docs_block, linked_docs_block
from documents.forms.quick import DocumentQuickForm


creme_registry.register_entity_models(Document, Folder)
creme_registry.register_app('documents', _(u'Documents'), '/documents')

reg_item = creme_menu.register_app('documents', '/documents/').register_item
reg_item('/documents/',             _(u'Portal of documents'), 'documents')
reg_item('/documents/documents',    _(u'All documents'),       'documents')
reg_item('/documents/document/add', _('Add a document'),       'documents.add_document')
reg_item('/documents/folders',      _(u'All folders'),         'documents')
reg_item('/documents/folder/add',   _('Add a folder'),         'documents.add_folder')

block_registry.register(folder_docs_block, linked_docs_block)

reg_icon = icon_registry.register
reg_icon(Document, 'images/document_%(size)s.png')
reg_icon(Folder,   'images/document_%(size)s.png')

bulk_update_registry.register(
    (Document, ['filedata']),
    (Folder,   ['parent_folder', 'category']),
)

reg_qform = quickforms_registry.register
reg_qform(Document,      DocumentQuickForm)
