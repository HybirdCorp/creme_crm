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

from django.forms import ValidationError
from django.utils.translation import ugettext as _

from creme.creme_core.forms import CremeEntityForm

from creme.documents.models.folder import Folder


class FolderForm(CremeEntityForm):
    class Meta(CremeEntityForm.Meta):
        model = Folder

    def clean_category(self):
        cleaned_data = self.cleaned_data
        parent_folder_data = cleaned_data['parent_folder']
        category_data      = cleaned_data['category']

        if parent_folder_data is not None and parent_folder_data.category != category_data:
            raise ValidationError(_(u"Folder's category must be the same than its parent's one: %s") % parent_folder_data.category)

        return category_data
