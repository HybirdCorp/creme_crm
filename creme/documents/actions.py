# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2018  Hybird
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

from django.urls.base import reverse
from django.utils.translation import ugettext as _

from creme import documents
from creme.creme_core.gui import actions


Folder   = documents.get_folder_model()
Document = documents.get_document_model()


class ExploreFolderActionEntry(actions.ActionEntry):
    action_id = 'documents-explore'
    action = 'redirect'

    model = Folder
    label = _('Explore')
    icon = 'view'

    @property
    def url(self):
        instance = self.instance
        return '{}?parent_id={}'.format(instance.get_lv_absolute_url(), instance.id)

    @property
    def is_enabled(self):
        return self.user.has_perm_to_view(self.instance)

    @property
    def help_text(self):
        return _('List sub-folders of «{}»').format(self.instance)


class DownloadActionEntry(actions.ActionEntry):
    action_id = 'documents-download'
    action = 'redirect'

    model = Document
    label = _('Download')
    icon = 'download'

    @property
    def url(self):
        return reverse('creme_core__dl_file', args=(self.instance.filedata,))

    @property
    def is_enabled(self):
        return self.user.has_perm_to_view(self.instance)

    @property
    def help_text(self):
        return _('Download the file')
