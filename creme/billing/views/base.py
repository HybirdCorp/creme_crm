# -*- coding: utf-8 -*-

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

# import warnings
from typing import Sequence, Union

from creme import persons
from creme.billing.forms import base as base_forms
from creme.billing.models import Base
from creme.creme_core.utils import bool_from_str_extended
from creme.creme_core.views import generic


class BaseCreation(generic.EntityCreation):
    model = Base
    initial_status = 1

    def get_initial(self):
        initial = super().get_initial()
        initial['status'] = self.initial_status

        return initial


class RelatedBaseCreation(generic.AddingInstanceToEntityPopup):
    model = Base
    # permissions: Union[str, Sequence[str], None] = 'billing'
    permissions: Union[str, Sequence[str]] = 'billing'  # Need creation perm too
    initial_status = 1
    entity_id_url_kwarg = 'target_id'
    entity_classes = [
        persons.get_organisation_model(),
        persons.get_contact_model(),
    ]
    entity_form_kwarg = None

    def get_initial(self):
        initial = super().get_initial()
        initial['status'] = self.initial_status

        target = self.get_related_entity()
        # initial['target'] = target  # DEPRECATED
        initial[
            base_forms.BillingTargetSubCell(model=self.model).into_cell().key
        ] = target

        return initial

    def get_success_url(self):
        if bool_from_str_extended(self.request.GET.get('redirection', '0')):
            return self.object.get_absolute_url()

        return super().get_success_url()


# class BaseEdition(generic.EntityEdition):
#     template_name = 'billing/form/edit.html'
#
#     def __init__(self, *args, **kwargs):
#         warnings.warn('billing.views.base.BaseEdition is deprecated.', DeprecationWarning)
#         super().__init__(*args, **kwargs)
