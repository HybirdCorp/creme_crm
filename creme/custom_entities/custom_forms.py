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

from django.utils.translation import gettext_lazy as _

from creme.creme_core.gui.custom_form import CustomFormDescriptor

from .models import all_custom_models

creation_descriptors = {
    model.custom_id: CustomFormDescriptor(
        id=f'custom_entities-creation{model.custom_id}',
        model=model,
        verbose_name=_('Creation form'),
        # default=CustomFormDefault,
    ) for model in all_custom_models
}
edition_descriptors = {
    model.custom_id: CustomFormDescriptor(
        id=f'custom_entities-edition{model.custom_id}',
        model=model,
        verbose_name=_('Edition form'),
        # default=CustomFormDefault,
    ) for model in all_custom_models
}
