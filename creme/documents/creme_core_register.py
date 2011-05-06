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

from django.utils.translation import ugettext_lazy as _

from creme_core.registry import creme_registry
from creme_core.gui.menu import creme_menu
from creme_core.gui.block import block_registry
from creme_core.gui.bulk_update import bulk_update_registry

from documents.models import Document, Folder
from documents.blocks import linked_docs_block


creme_registry.register_entity_models(Document, Folder)
creme_registry.register_app('documents', _(u'Documents'), '/documents')

reg_item = creme_menu.register_app('documents', '/documents/').register_item
reg_item('/documents/',             _(u'Portal'),        'documents')
reg_item('/documents/documents',    _(u'All documents'), 'documents')
reg_item('/documents/document/add', _('Add a document'), 'documents.add_document')
reg_item('/documents/folders',      _(u'All folders'),   'documents')
reg_item('/documents/folder/add',   _('Add a folder'),   'documents.add_folder')

block_registry.register(linked_docs_block)

bulk_update_registry.register(
    (Document, ['filedata']),
    (Folder, ['parent_folder', 'category']),#Even if Folders haven't currently a list_view
)
