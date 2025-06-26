################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2024-2025  Hybird
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

from datetime import date

from django.contrib.contenttypes.models import ContentType
from django.db.transaction import atomic
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.models.utils import assign_2_charfield
from creme.creme_core.views import generic
from creme.creme_core.views.decorators import workflow_engine

from .. import get_invoice_model
from ..core.number_generation import number_generator_registry
from ..models import Base, InvoiceStatus, NumberGeneratorItem


class NumberGeneratorEdition(generic.CremeModelEditionPopup):
    model = NumberGeneratorItem
    permissions = 'billing.can_admin'
    pk_url_kwarg = 'item_id'
    title = _(
        'Edit the configuration of «{object.numbered_type}» for «{object.organisation}»'
    )

    generator_registry = number_generator_registry

    def get_form_class(self):
        return self.generator_registry[self.object].form_class


class NumberGeneration(generic.base.EntityRelatedMixin, generic.CheckedView):
    permissions = 'billing'

    generator_registry = number_generator_registry

    def check_related_entity_permissions(self, entity, user):
        pass  # We use generator instead

    def _generate_number(self, entity):
        model = type(entity)

        if not issubclass(model, Base):
            raise ConflictError('The entity must be a billing entity')

        if model.generate_number_in_create:
            raise ConflictError(
                _('The number is generated at creation for this kind of entity')
            )

        # NB: we take care to always retrieve the Organisation & after the Item
        #     to avoid deadlock
        item = get_object_or_404(
            NumberGeneratorItem.objects.select_for_update(),
            numbered_type=ContentType.objects.get_for_model(model),
            organisation=entity.source,
        )

        gen = self.generator_registry[item]
        gen.check_permissions(user=self.request.user, entity=entity)

        return gen.perform()

    def _extra_process(self, entity):
        if isinstance(entity, get_invoice_model()):
            if status := InvoiceStatus.objects.filter(is_validated=True).first():
                entity.status = status

        if not entity.issuing_date:
            entity.issuing_date = date.today()

    @atomic
    @method_decorator(workflow_engine)
    def post(self, *args, **kwargs):
        entity = self.get_related_entity()

        # TODO: log if too long?
        assign_2_charfield(entity, field_name='number', value=self._generate_number(entity))
        self._extra_process(entity)
        entity.save()

        return HttpResponse()
