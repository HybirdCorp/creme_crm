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

from __future__ import annotations

from datetime import date

from django.db.models import Model
from django.http import HttpResponse
from django.utils.translation import gettext_lazy as _

from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.views import generic

from .. import get_invoice_model, models
from ..core.number_generation import NumberGenerator, number_generator_registry


class NumberGeneratorMixin:
    generator_registry = number_generator_registry

    def get_number_generator(self, model: type[Model]) -> NumberGenerator:
        if not issubclass(model, models.Base):
            raise ConflictError('The entity must be a billing entity')

        gen = self.generator_registry.get(model)
        if gen is None:
            raise ConflictError(
                _('This kind of entity cannot not generate a number.')
            )

        return gen


class NumberGeneratorEdition(NumberGeneratorMixin,
                             generic.CremeModelEditionPopup):
    model = models.NumberGeneratorItem
    permissions = 'billing.can_admin'
    pk_url_kwarg = 'item_id'
    title = _(
        'Edit the configuration of «{object.numbered_type}» for «{object.organisation}»'
    )

    def get_form_class(self):
        return self.get_number_generator(
            model=self.object.numbered_type.model_class()
        ).form_class


class NumberGeneration(generic.base.EntityRelatedMixin,
                       NumberGeneratorMixin,
                       generic.CheckedView):
    permissions = 'billing'

    def _generate_number(self, entity):
        gen = self.get_number_generator(model=type(entity))
        if gen.trigger_at_creation:
            raise ConflictError(
                _('The number is generated at creation for this kind of entity')
            )

        # TODO: move to generator (to disable button/action) + permissions checking
        if entity.number:
            raise ConflictError(_('This entity has already a number'))

        return gen.perform(organisation=entity.source)

    def _extra_process(self, entity):
        if isinstance(entity, get_invoice_model()):
            if status := models.InvoiceStatus.objects.filter(is_validated=True).first():
                entity.status = status

        # if not entity.issuing_date:  TODO
        entity.issuing_date = date.today()

    # TODO: <@atomic>?
    def post(self, *args, **kwargs):
        # TODO: select_for_update()
        entity = self.get_related_entity()

        entity.number = self._generate_number(entity)
        self._extra_process(entity)
        entity.save()

        return HttpResponse()
