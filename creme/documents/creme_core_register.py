# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2015  Hybird
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

from django.core.urlresolvers import reverse_lazy as reverse
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.auth import build_creation_perm
from creme.creme_core.registry import creme_registry
from creme.creme_core.gui import (creme_menu, block_registry, icon_registry,
        bulk_update_registry, quickforms_registry, merge_form_registry)

from . import get_document_model, get_folder_model
from .blocks import folder_docs_block, child_folders_block, linked_docs_block
from .forms.quick import DocumentQuickForm
from .forms.folder import ParentFolderBulkForm, get_merge_form_builder
#from .models import Document, Folder


Document = get_document_model()
Folder   = get_folder_model()

creme_registry.register_entity_models(Document, Folder)
creme_registry.register_app('documents', _(u'Documents'), '/documents')

reg_item = creme_menu.register_app('documents', '/documents/').register_item
reg_item('/documents/',             _(u'Portal of documents'), 'documents')
#reg_item('/documents/documents',    _(u'All documents'),       'documents')
#reg_item('/documents/document/add', Document.creation_label,   'documents.add_document')
#reg_item('/documents/folders',      _(u'All folders'),         'documents')
#reg_item('/documents/folder/add',   Folder.creation_label,     'documents.add_folder')
reg_item(reverse('documents__list_documents'),  _(u'All documents'),     'documents')
reg_item(reverse('documents__create_document'), Document.creation_label, build_creation_perm(Document))
reg_item(reverse('documents__list_folders'),    _(u'All folders'),       'documents')
reg_item(reverse('documents__create_folder'),   Folder.creation_label,   build_creation_perm(Folder))

block_registry.register(folder_docs_block, child_folders_block, linked_docs_block)

reg_icon = icon_registry.register
reg_icon(Document, 'images/document_%(size)s.png')
reg_icon(Folder,   'images/document_%(size)s.png')

merge_form_registry.register(Folder, get_merge_form_builder)

bulk_update_registry.register(Folder, innerforms={'parent_folder': ParentFolderBulkForm})
bulk_update_registry.register(Document, exclude=['filedata'])

quickforms_registry.register(Document, DocumentQuickForm)
