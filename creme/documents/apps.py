# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2016  Hybird
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

from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.apps import CremeAppConfig


class DocumentsConfig(CremeAppConfig):
    name = 'creme.documents'
    verbose_name = _(u'Documents')
    dependencies = ['creme.creme_core']

    def all_apps_ready(self):
        from . import get_document_model, get_folder_model

        self.Document = get_document_model()
        self.Folder   = get_folder_model()
        super(DocumentsConfig, self).all_apps_ready()

    def register_creme_app(self, creme_registry):
        creme_registry.register_app('documents', _(u'Documents'), '/documents')

    def register_entity_models(self, creme_registry):
        creme_registry.register_entity_models(self.Document, self.Folder)

    def register_blocks(self, block_registry):
        from . import blocks

        block_registry.register_4_model(self.Document, blocks.DocumentBlock())
        block_registry.register(blocks.folder_docs_block,
                                blocks.child_folders_block,
                                blocks.linked_docs_block,
                               )

    def register_bulk_update(self, bulk_update_registry):
        from .forms.folder import ParentFolderBulkForm

        register = bulk_update_registry.register
        register(self.Folder, innerforms={'parent_folder': ParentFolderBulkForm})
        register(self.Document, exclude=['filedata'])

    def register_field_printers(self, field_printers_registry):
        from creme.creme_core.gui.field_printers import print_foreignkey_html, print_many2many_html

        def print_fk_image_html(entity, fval, user, field):
            if not user.has_perm_to_view(fval):
                return settings.HIDDEN_VALUE

            mime_type = fval.mime_type

            if mime_type and mime_type.is_image:
                return u'''<a onclick="creme.dialogs.image('%s').open();"%s>%s</a>''' % (
                        fval.get_dl_url(),
                        ' class="is_deleted"' if fval.is_deleted else u'',
                        fval.get_entity_summary(user)
                    )

            return print_foreignkey_html.print_fk_entity_html(entity, fval, user, field)

        def print_doc_summary_html(instance, related_entity, fval, user, field):
            if not user.has_perm_to_view(instance):
                return settings.HIDDEN_VALUE

            mime_type = instance.mime_type

            if mime_type and mime_type.is_image:
                return u'''<a onclick="creme.dialogs.image('%s').open();"%s>%s</a>''' % (
                            instance.get_dl_url(),
                            ' class="is_deleted"' if instance.is_deleted else u'',
                            instance.get_entity_summary(user),
                        )

            return print_many2many_html.printer_entity_html(instance, related_entity, fval, user, field)

        Document = self.Document
        print_foreignkey_html.register(Document, print_fk_image_html)
        print_many2many_html.register(Document,
                                      printer=print_doc_summary_html,
                                      enumerator=print_many2many_html.enumerator_entity,
                                     )

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
