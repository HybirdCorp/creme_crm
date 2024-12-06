################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2024  Hybird
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

from django.utils.translation import gettext as _

from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.forms import CremeModelForm
from creme.creme_core.models import CustomEntityType, HeaderFilter


class CustomEntityTypeCreationForm(CremeModelForm):
    class Meta(CremeModelForm.Meta):
        model = CustomEntityType

    # TODO: @atomic?
    def save(self, *args, **kwargs):
        instance = self.instance
        instance.number = type(instance).objects.count() + 1

        super().save(*args, **kwargs)

        HeaderFilter.objects.create_if_needed(
            pk=f'creme_core-hf_custom_entity_{instance.number}',  # TODO: .id
            name=_('{model} view').format(model=instance.name),
            model=instance.entity_model,
            is_custom=False,
            cells_desc=[(EntityCellRegularField, {'name': 'name'})],
        )

        return instance


class CustomEntityTypeEditionForm(CremeModelForm):
    class Meta(CremeModelForm.Meta):
        model = CustomEntityType
