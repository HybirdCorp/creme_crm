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

from django.http import Http404
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.forms import CremeEntityForm
from creme.creme_core.models.custom_entity import CustomEntityType
from creme.creme_core.views import generic


class CustomEntityMixin:
    type_id_url_kwargs = 'type_id'

    _custom_type = False

    def get_custom_type(self):
        ce_type = self._custom_type

        if ce_type is False:
            self._custom_type = ce_type = CustomEntityType.objects.get_for_id(
                int(self.kwargs.get(self.type_id_url_kwargs))
            )
            if ce_type is None or not ce_type.enabled:
                raise Http404(gettext('This custom entity type seems invalid'))

        return ce_type


class CustomEntityCreation(CustomEntityMixin, generic.EntityCreation):
    title = _('Create a «{custom_model}»')

    @property
    def model(self):
        ce_type = self.get_custom_type()
        if ce_type.deleted:
            raise ConflictError(gettext(
                'You cannot create an entity because the custom type is deleted.'
            ))

        return ce_type.entity_model

    # TODO: custom form?
    @property
    def form_class(self):
        class CustomForm(CremeEntityForm):
            class Meta:
                model = self.model
                fields = ('user', 'name',)

        return CustomForm

    def get_title_format_data(self):
        data = super().get_title_format_data()
        data['custom_model'] = self.get_custom_type().name

        return data


class CustomEntityEdition(CustomEntityMixin, generic.EntityEdition):
    @property
    def model(self):
        ce_type = self.get_custom_type()
        if ce_type.deleted:
            raise ConflictError(gettext(
                'You cannot edit this entity because the custom type is deleted.'
            ))

        return ce_type.entity_model

    # TODO: factorise
    @property
    def form_class(self):
        class CustomForm(CremeEntityForm):
            class Meta:
                model = self.model
                fields = ('user', 'name',)

        return CustomForm


# TODO: disable the edition button when the type is deleted
class CustomEntityDetail(CustomEntityMixin, generic.EntityDetail):
    @property
    def model(self):
        return self.get_custom_type().entity_model


# TODO: disable the creation button when the type is deleted
class CustomEntitiesList(CustomEntityMixin, generic.EntitiesList):
    # default_headerfilter_id = ...

    @property
    def model(self):
        return self.get_custom_type().entity_model

    def get_title_format_data(self) -> dict:
        data = super().get_title_format_data()
        data['models'] = self.get_custom_type().plural_name

        return data
