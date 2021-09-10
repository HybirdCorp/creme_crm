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

from typing import Optional, Sequence

from django.core.exceptions import ImproperlyConfigured
from django.db.models import Model, QuerySet
from django.db.transaction import atomic
from django.http import Http404, HttpResponse
from django.views.generic import View

from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.utils import get_from_POST_or_404


class ReorderInstances(View):
    """Base view to re-order an instance among other instances.
    The model must have an ordering integer field.

    Attributes:
     - model & queryset: use to build the QuerySet of re-ordered instances
            ( see get_queryset() ).
     - pk_url_kwarg: Name of the kwargs (ie URL parameter) containing the PK
            of the moved instance.
     - target_order_post_argument: Name of the POST argument containing the new
            order of the moved instance.
     - order_field_name: Name of the model field used for ordering.
     - use_select_for_update: True means that .select_for_update() will be called
            on the instances queryset.

    Notice:
    the values for 'order_field' are automatically re-mapped on [1, 2 ...]
    (so even if the global ordering of an instance has not changed, the value
    of its order-field could change).
    """
    model: Optional[Model] = None
    queryset: Optional[QuerySet] = None
    pk_url_kwarg: str = 'object_id'
    target_order_post_argument: str = 'target'
    order_field_name: str = 'order'
    use_select_for_update = True

    def get_moved_instance_index(self, instances: Sequence[Model]) -> Optional[int]:
        """Returns the index of the instance we want to move.

        @param instances: List of instances we will re-order.
        @return: 0-based index (instances[this_index] == wanted_instance).
                 <None> means the instance has not been found.
        """
        if instances:
            pk = instances[0]._meta.pk.to_python(self.kwargs[self.pk_url_kwarg])

            for index, instance in enumerate(instances):
                if pk == instance.pk:
                    return index

        return None

    def get_queryset(self) -> QuerySet:
        """Returns all the instances which will been re-ordered.

        Notice: no need to order this queryset (it's done automatically).
        """
        if self.queryset is None:
            if self.model is not None:
                return self.model._default_manager.all()

            raise ImproperlyConfigured(
                '{cls} is missing a QuerySet. Define {cls}.model, '
                '{cls}.queryset, or override {cls}.get_queryset().'.format(
                    cls=self.__class__.__name__,
                )
            )

        return self.queryset.all()

    def get_target_order(self) -> int:
        """Returns the future order (starting at 1) of the instance we want to move."""
        order = get_from_POST_or_404(self.request.POST, self.target_order_post_argument, int)
        if order < 1:
            raise ConflictError('Target order must be greater than or equal to 1.')

        return order

    def post(self, request, *args, **kwargs):
        new_order = self.get_target_order()
        order_fname = self.order_field_name

        with atomic():
            # NB: inside the atomic block to eventually perform a select_for_update().
            qs = self.get_queryset().order_by(order_fname)

            instances = list(qs.select_for_update() if self.use_select_for_update else qs)

            target_index = self.get_moved_instance_index(instances)
            if target_index is None:
                raise Http404('Target instance not found.')

            moved_instance = instances.pop(target_index)

            new_order = min(new_order, len(instances))  # Resists to a race deletion
            instances.insert(new_order - 1, moved_instance)

            for index, instance in enumerate(instances, start=1):
                old_order = getattr(instance, order_fname)

                if old_order != index:
                    setattr(instance, order_fname, index)
                    instance.save(force_update=True, update_fields=(order_fname,))

        return HttpResponse()
