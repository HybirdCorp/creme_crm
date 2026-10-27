################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2026  Hybird
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

from django.contrib.contenttypes.models import ContentType

from creme import billing
from creme.billing import models as billing_models
from creme.creme_core.core.soft_reference import SoftReferenceCollector
from creme.creme_core.models import MinionModel


class TemplateBaseStatusRefCollector(SoftReferenceCollector):
    # TODO
    # """Collect the RelationTypes which reference a CremePropertyType through their
    # constraints to allowed & forbidden Property types.
    #
    # Notice that these references are stored in ManyToManyFields, & this type of
    # fields has no attribute 'on_delete' like ForeignKeys.
    # """
    id = 'billing-template-status'
    model = MinionModel

    models_map = {
        billing_models.CreditNoteStatus:    billing.get_credit_note_model(),
        billing_models.InvoiceStatus:       billing.get_invoice_model(),
        billing_models.QuoteStatus:         billing.get_quote_model(),
        billing_models.SalesOrderStatus:    billing.get_sales_order_model(),
    }

    def collect(self, instance):
        assert isinstance(instance, self.model)

        entity_model = self.models_map.get(type(instance))
        if entity_model:
            yield from billing.get_template_base_model().objects.filter(
                status_uuid=instance.uuid,
                ct=ContentType.objects.get_for_model(entity_model),
            )
