################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2022  Hybird
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

from creme.creme_core.forms import CremeEntityForm
from creme.creme_core.views.file_handling import handle_uploaded_file


class BaseDocumentCustomForm(CremeEntityForm):
    def save(self, *args, **kwargs):
        instance = self.instance
        file_data = self.cleaned_data.get('filedata')

        if file_data:
            file_field = type(instance)._meta.get_field('filedata')
            instance.filedata = handle_uploaded_file(
                file_data,
                path=file_field.upload_to.split('/'),
                max_length=file_field.max_length,
            )

        return super().save(*args, **kwargs)
