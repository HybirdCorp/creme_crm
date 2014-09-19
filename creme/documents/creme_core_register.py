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

from django.utils.translation import ugettext_lazy as _

from creme.creme_core.registry import creme_registry
from creme.creme_core.gui import creme_menu, block_registry, icon_registry, bulk_update_registry, quickforms_registry

from .models import Document, Folder
from .blocks import folder_docs_block, linked_docs_block
from .forms.quick import DocumentQuickForm


creme_registry.register_entity_models(Document, Folder)
creme_registry.register_app('documents', _(u'Documents'), '/documents')

reg_item = creme_menu.register_app('documents', '/documents/').register_item
reg_item('/documents/',             _(u'Portal of documents'), 'documents')
reg_item('/documents/documents',    _(u'All documents'),       'documents')
reg_item('/documents/document/add', Document.creation_label,   'documents.add_document')
reg_item('/documents/folders',      _(u'All folders'),         'documents')
reg_item('/documents/folder/add',   Folder.creation_label,     'documents.add_folder')

block_registry.register(folder_docs_block, linked_docs_block)

reg_icon = icon_registry.register
reg_icon(Document, 'images/document_%(size)s.png')
reg_icon(Folder,   'images/document_%(size)s.png')

bulk_update_registry.register(Document, exclude=['filedata'])
bulk_update_registry.register(Folder)

quickforms_registry.register(Document, DocumentQuickForm)
