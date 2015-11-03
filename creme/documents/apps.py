# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015  Hybird
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

from creme.creme_core.apps import CremeAppConfig


class DocumentsConfig(CremeAppConfig):
    name = 'creme.documents'
    verbose_name = _(u'Documents')
    dependencies = ['creme.creme_core']

#    def ready(self):
    def all_apps_ready(self):
        from . import get_document_model, get_folder_model

        self.Document = get_document_model()
        self.Folder   = get_folder_model()
#        super(DocumentsConfig, self).ready()
        super(DocumentsConfig, self).all_apps_ready()

    def register_creme_app(self, creme_registry):
        creme_registry.register_app('documents', _(u'Documents'), '/documents')

    def register_entity_models(self, creme_registry):
        creme_registry.register_entity_models(self.Document, self.Folder)

    def register_blocks(self, block_registry):
        from .blocks import folder_docs_block, child_folders_block, linked_docs_block

        block_registry.register(folder_docs_block, child_folders_block, linked_docs_block)

    def register_bulk_update(self, bulk_update_registry):
        from .forms.folder import ParentFolderBulkForm

        register = bulk_update_registry.register
        register(self.Folder, innerforms={'parent_folder': ParentFolderBulkForm})
        register(self.Document, exclude=['filedata'])

    def register_icons(self, icon_registry):
        reg_icon = icon_registry.register
        reg_icon(self.Document, 'images/document_%(size)s.png')
        reg_icon(self.Folder,   'images/document_%(size)s.png')

    def register_menu(self, creme_menu):
        from django.core.urlresolvers import reverse_lazy as reverse

        from creme.creme_core.auth import build_creation_perm as cperm

        Document = self.Document
        Folder   = self.Folder
        reg_item = creme_menu.register_app('documents', '/documents/').register_item
        reg_item('/documents/',                         _(u'Portal of documents'), 'documents')
        reg_item(reverse('documents__list_documents'),  _(u'All documents'),       'documents')
        reg_item(reverse('documents__create_document'), Document.creation_label,    cperm(Document))
        reg_item(reverse('documents__list_folders'),    _(u'All folders'),         'documents')
        reg_item(reverse('documents__create_folder'),   Folder.creation_label,     cperm(Folder))

    def register_merge_forms(self, merge_form_registry):
        from .forms.folder import get_merge_form_builder

        merge_form_registry.register(self.Folder, get_merge_form_builder)

    def register_quickforms(self, quickforms_registry):
        from .forms.quick import DocumentQuickForm

        quickforms_registry.register(self.Document, DocumentQuickForm)
