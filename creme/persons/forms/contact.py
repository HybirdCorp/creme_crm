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

from creme import persons
from creme.creme_core.forms import CremeEntityForm, CremeModelForm


class ContactNamesForm(CremeModelForm):
    class Meta(CremeModelForm.Meta):
        model = persons.get_contact_model()
        fields = ('last_name', 'first_name')


class BaseContactCustomForm(CremeEntityForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance.is_user_id:
            get_field = self.fields.get

            for field_name in ('first_name', 'email'):
                field = get_field(field_name)
                if field is not None:
                    field.required = True
