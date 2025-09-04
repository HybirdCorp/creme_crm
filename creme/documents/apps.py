################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2025  Hybird
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

from django.utils.translation import gettext_lazy as _

from creme.creme_core.apps import CremeAppConfig


class DocumentsConfig(CremeAppConfig):
    default = True
    name = 'creme.documents'
    verbose_name = _('Documents')
    dependencies = ['creme.creme_core']

    def all_apps_ready(self):
        from . import get_document_model, get_folder_model

        self.Document = get_document_model()
        self.Folder   = get_folder_model()
        super().all_apps_ready()

    def register_entity_models(self, creme_registry):
        creme_registry.register_entity_models(self.Document, self.Folder)

    # def register_actions(self, actions_registry):
    def register_actions(self, action_registry):
        from . import actions

        # actions_registry.register_instance_actions(
        action_registry.register_instance_actions(
            actions.ExploreFolderAction,
            actions.DownloadAction,
        )

    def register_bricks(self, brick_registry):
        from . import bricks

        Document = self.Document
        brick_registry.register_4_model(
            Document, bricks.DocumentBrick,
        ).register(
            bricks.FolderDocsBrick,
            bricks.ChildFoldersBrick,
            bricks.LinkedDocsBrick,
        ).register_hat(
            Document, main_brick_cls=bricks.DocumentBarHatBrick,
        )

    def register_bulk_update(self, bulk_update_registry):
        from .forms.folder import ParentFolderOverrider

        register = bulk_update_registry.register
        register(self.Folder).add_overriders(ParentFolderOverrider)
        # NB: <filedata> is currently not (inner)-editable to avoid the
        #     overriding of the previous file without rollback possibility.
        #     Should we implement a file versioning system?
        register(self.Document).exclude('filedata')

    def register_creme_config(self, config_registry):
        from . import models

        register_model = config_registry.register_model
        register_model(models.FolderCategory,   'category')
        register_model(models.DocumentCategory, 'doc_category')

    def register_custom_forms(self, cform_registry):
        from . import custom_forms

        cform_registry.register(
            custom_forms.FOLDER_CREATION_CFORM,
            custom_forms.FOLDER_EDITION_CFORM,

            custom_forms.DOCUMENT_CREATION_CFORM,
            custom_forms.DOCUMENT_EDITION_CFORM,
        )

    def register_cloners(self, entity_cloner_registry):
        from . import cloners

        entity_cloner_registry.register(
            model=self.Folder, cloner_class=cloners.FolderCloner,
        )
        # TODO?
        #  register(model=self.Document)

    def register_deletors(self, entity_deletor_registry):
        from . import deletors

        entity_deletor_registry.register(
            model=self.Folder, deletor_class=deletors.FolderDeletor,
        ).register(
            model=self.Document,
        )

    def register_fields_config(self, fields_config_registry):
        fields_config_registry.register_models(self.Document, self.Folder)

    def register_field_printers(self, field_printer_registry):
        from django.db import models

        from . import gui

        Document = self.Document
        printers = field_printer_registry.printers_for_field_type

        for field in (models.ForeignKey, models.OneToOneField):
            for printer in printers(type=field, tags='html*'):
                printer.register(model=Document, printer=gui.print_fk_image_html)

        for printer in printers(type=models.ManyToManyField, tags='html*'):
            printer.register(
                model=Document,
                printer=gui.print_doc_summary_html,
                enumerator=printer.enumerator_entity,
            )

    def register_filefields_download(self, filefield_download_registry):
        filefield_download_registry.register(
            model=self.Document, field_name='filedata',
        )

    def register_icons(self, icon_registry):
        icon_registry.register(
            self.Document, 'images/document_%(size)s.png',
        ).register(
            self.Folder,   'images/document_%(size)s.png',
        )

    def register_menu_entries(self, menu_registry):
        from . import menu

        menu_registry.register(
            menu.DocumentsEntry, menu.DocumentCreationEntry,
            menu.FoldersEntry,   menu.FolderCreationEntry,
        )

    def register_creation_menu(self, creation_menu_registry):
        creation_menu_registry.get_or_create_group(
            'tools', _('Tools'), priority=100
        ).add_link(
            'documents-create_document', self.Document, priority=10,
        ).add_link(
            'documents-create_folder',   self.Folder,   priority=20,
        )

    def register_merge_forms(self, merge_form_registry):
        from .forms import folder

        merge_form_registry.register(self.Folder, folder.get_merge_form_builder)

    def register_quickforms(self, quickform_registry):
        from .forms import quick

        quickform_registry.register(self.Document, quick.DocumentQuickForm)
