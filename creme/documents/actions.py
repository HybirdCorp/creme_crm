################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2018-2021  Hybird
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

from creme import documents
from creme.creme_core.gui.actions import UIAction

Folder   = documents.get_folder_model()
Document = documents.get_document_model()


class ExploreFolderAction(UIAction):
    id = UIAction.generate_id('documents', 'explore')
    model = Folder

    type = 'redirect'

    label = _('Explore')
    icon = 'view'

    help_format = _('List sub-folders of «{}»')

    @property
    def url(self):
        instance = self.instance
        return f'{instance.get_lv_absolute_url()}?parent_id={instance.id}'

    @property
    def is_enabled(self):
        return self.user.has_perm_to_view(self.instance)

    @property
    def help_text(self):
        return self.help_format.format(self.instance)


class DownloadAction(UIAction):
    id = UIAction.generate_id('documents', 'download')
    model = Document

    type = 'redirect'

    label = _('Download')
    icon = 'download'

    help_text = _('Download the file')

    @property
    def url(self):
        return self.instance.get_download_absolute_url()

    @property
    def is_enabled(self):
        return self.user.has_perm_to_view(self.instance)
