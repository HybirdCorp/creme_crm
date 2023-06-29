################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2019-2023  Hybird
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
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from creme.creme_core.gui import listview
from creme.creme_core.gui.field_printers import FKPrinter, M2MPrinterForHTML

from . import get_folder_model

Folder = get_folder_model()


# List-view Buttons ------------------------------------------------------------
class ParentFolderButton(listview.ListViewButton):
    # NB: use context variable "parent_folder" (see FoldersList).
    template_name = 'documents/listview/buttons/parent-folder.html'


class FolderCreationButton(listview.CreationButton):
    label_subfolder = _('Create a sub-folder for «{entity}»')

    def get_label(self, request, model):
        parent = self.context['parent_folder']

        return (
            self.label_subfolder.format(entity=parent)
            if parent else
            super().get_label(request=request, model=model)
        )

    def get_url(self, request, model):
        parent = self.context['parent_folder']

        return (
            reverse('documents__create_folder', args=(parent.id,))
            if parent else
            super().get_url(request=request, model=model)
        )

    def is_allowed(self, request, model):
        allowed = super().is_allowed(request=request, model=model)

        parent = self.context['parent_folder']
        if parent:
            allowed &= request.user.has_perm_to_link(Folder, owner=None)

        return allowed


# Field printers ---------------------------------------------------------------
def print_fk_image_html(*, value, user, **kwargs):
    if not user.has_perm_to_view(value):
        return settings.HIDDEN_VALUE

    mime_type = value.mime_type

    if mime_type and mime_type.is_image:
        return format_html(
            '''<a onclick="creme.dialogs.image('{url}').open();"{attrs}>{content}</a>''',
            url=value.get_download_absolute_url(),
            attrs=mark_safe(' class="is_deleted"' if value.is_deleted else ''),
            content=value.get_entity_summary(user),
        )

    return FKPrinter.print_fk_entity_html(value=value, user=user, **kwargs)


def print_doc_summary_html(*, instance, user, **kwargs):
    if not user.has_perm_to_view(instance):
        return settings.HIDDEN_VALUE

    mime_type = instance.mime_type

    if mime_type and mime_type.is_image:
        return format_html(
            '''<a onclick="creme.dialogs.image('{url}').open();"{attrs}>{content}</a>''',
            url=instance.get_download_absolute_url(),
            attrs=mark_safe(' class="is_deleted"' if instance.is_deleted else ''),
            content=instance.get_entity_summary(user),
        )

    return M2MPrinterForHTML.printer_entity(
        instance=instance, user=user, **kwargs
    )
