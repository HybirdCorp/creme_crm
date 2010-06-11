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

from creme_core.forms import CremeModelForm

from documents.models.folder import Folder


class FolderForm(CremeModelForm):
    class Meta:
        model = Folder
        exclude = CremeModelForm.exclude

    def clean_category(self):
        parent_folder_data = self.cleaned_data['parent_folder']
        category_data = self.cleaned_data['category']
#        if parent_folder_data is not None and category_data is not None and parent_folder_data.category != category_data:
        if parent_folder_data is not None and parent_folder_data.category != category_data:
            raise ValidationError("La categorie du classeur doit être la même que celle du parent : %s" % parent_folder_data.category)

        return category_data
