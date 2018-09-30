# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2018  Hybird
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

from creme.creme_core.views import generic

from creme.billing.models import Base
# from creme.billing.forms.base import BaseCreateForm

from creme import persons


class BaseCreation(generic.EntityCreation):
    model = Base
    # form_class = BaseCreateForm
    initial_status = 1

    def get_initial(self):
        initial = super().get_initial()
        initial['status'] = self.initial_status

        return initial


class RelatedBaseCreation(generic.AddingToEntity):
    model = Base
    # form_class = BaseCreateForm
    permissions = 'billing'  # Need creation perm too
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
        initial['target'] = self.get_related_entity()

        return initial
