################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2024  Hybird
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

from creme.creme_core import forms as core_forms
from creme.creme_core.models import CremePropertyType


class CremePropertyForm(core_forms.CremeModelForm):
    # TODO: formfield_callback???
    subject_ctypes = core_forms.MultiEntityCTypeChoiceField(
        label=_('Related to types of entities'),
        help_text=_('No selected type means that all types are accepted'),
        required=False,
    )

    class Meta(core_forms.CremeModelForm.Meta):
        model = CremePropertyType

    def save(self, *args, **kwargs):
        self.instance.is_custom = True
        return super().save(*args, **kwargs)
