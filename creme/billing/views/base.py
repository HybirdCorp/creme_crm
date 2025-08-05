################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2018-2025  Hybird
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
from collections.abc import Sequence

import creme.billing.forms.base as base_forms
from creme import persons
from creme.billing.constants import REL_SUB_BILL_ISSUED
from creme.billing.models import Base
from creme.creme_core.core.entity_cell import EntityCellRelation
from creme.creme_core.models import RelationType
from creme.creme_core.utils import bool_from_str_extended
from creme.creme_core.views import generic


# class BaseCreation(generic.EntityCreation):
#     model = Base
#
#     def __init__(self, **kwargs):
#         super().__init__(**kwargs)
#         warnings.warn(
#             'The class billing.views.base.BaseCreation is deprecated.',
#             DeprecationWarning,
#         )
#
#     def get_initial(self):
#         initial = super().get_initial()
#         status = (
#             self.model._meta.get_field('status')
#                             .related_model.objects.filter(is_default=True)
#                             .first()
#         )
#         if status is not None:
#             initial['status'] = status.id
#
#         return initial
class RelatedBaseCreation(generic.AddingInstanceToEntityPopup):
    model = Base
    permissions: str | Sequence[str] = 'billing'  # Need creation perm too
    entity_id_url_kwarg = 'target_id'
    entity_classes = [
        persons.get_organisation_model(),
        persons.get_contact_model(),
    ]
    entity_form_kwarg = None

    def get_initial(self):
        initial = super().get_initial()
        initial[
            base_forms.BillingTargetSubCell(model=self.model).into_cell().key
        ] = self.get_related_entity()

        return initial

    def get_success_url(self):
        if bool_from_str_extended(self.request.GET.get('redirection', '0')):
            return self.object.get_absolute_url()

        return super().get_success_url()


class BaseList(generic.EntitiesList):
    model = Base

    def get_cells(self, hfilter):
        cells = super().get_cells(hfilter=hfilter)
        model = self.model

        if not model.generate_number_in_create:
            # NB: add relations items to use the pre-cache system of list-views
            #     (see <EntitiesList.paginate_queryset()>)
            #     So we avoid extra queries when <billing.actions._GenerateNumberAction>
            #     uses <entity.source> to check permissions.
            # TODO: do we need a system in UIAction to prefetch things?
            rtype = RelationType.objects.get(pk=REL_SUB_BILL_ISSUED)
            cell = EntityCellRelation(model=model, rtype=rtype, is_hidden=True)
            key = cell.key
            if not any(key == c.key for c in cells):
                cells.append(cell)

        return cells
