################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2018-2024  Hybird
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

from __future__ import annotations

from typing import Sequence

import creme.billing.forms.base as base_forms
from creme import persons
from creme.billing.models import Base
from creme.creme_core.utils import bool_from_str_extended
from creme.creme_core.views import generic


class BaseCreation(generic.EntityCreation):
    model = Base
    # initial_status = 1

    def get_initial(self):
        initial = super().get_initial()
        # initial['status'] = self.initial_status
        # TODO: in models instead?
        status = (
            self.model._meta.get_field('status')
                            .related_model.objects.filter(is_default=True)
                            .first()
        )
        if status is not None:
            initial['status'] = status.id

        return initial


class RelatedBaseCreation(generic.AddingInstanceToEntityPopup):
    model = Base
    permissions: str | Sequence[str] = 'billing'  # Need creation perm too
    # initial_status = 1
    entity_id_url_kwarg = 'target_id'
    entity_classes = [
        persons.get_organisation_model(),
        persons.get_contact_model(),
    ]
    entity_form_kwarg = None

    def get_initial(self):
        initial = super().get_initial()
        # initial['status'] = self.initial_status
        status = (
            self.model._meta.get_field('status')
            .related_model.objects.filter(is_default=True)
            .first()
        )
        if status is not None:
            initial['status'] = status.id

        target = self.get_related_entity()
        initial[
            base_forms.BillingTargetSubCell(model=self.model).into_cell().key
        ] = target

        return initial

    def get_success_url(self):
        if bool_from_str_extended(self.request.GET.get('redirection', '0')):
            return self.object.get_absolute_url()

        return super().get_success_url()
