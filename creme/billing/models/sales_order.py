################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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
from django.db.models import ForeignKey
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from creme.creme_core.models import CREME_REPLACE

# from .. import get_template_base_model
from .base import Base
# from .templatebase import TemplateBase
from .other_models import SalesOrderStatus, get_default_sales_order_status_pk


class AbstractSalesOrder(Base):
    status = ForeignKey(
        SalesOrderStatus,
        verbose_name=_('Status of salesorder'),
        on_delete=CREME_REPLACE,
        default=get_default_sales_order_status_pk,
    )

    creation_label = _('Create a salesorder')
    save_label     = _('Save the salesorder')

    search_score = 50

    class Meta(Base.Meta):
        abstract = True
        verbose_name = _('Salesorder')
        verbose_name_plural = _('Salesorders')

    def get_absolute_url(self):
        return reverse('billing__view_order', args=(self.id,))

    @staticmethod
    def get_create_absolute_url():
        return reverse('billing__create_order')

    def get_edit_absolute_url(self):
        return reverse('billing__edit_order', args=(self.id,))

    @staticmethod
    def get_lv_absolute_url():
        return reverse('billing__list_orders')

    # def build(self, template):
    #     warnings.warn(
    #         'The method billing.models.SalesOrder.build() is deprecated.',
    #         DeprecationWarning,
    #     )
    #
    #     status = None
    #
    #     if isinstance(template, get_template_base_model()):
    #         status = SalesOrderStatus.objects.filter(uuid=template.status_uuid).first()
    #
    #     self.status = status or SalesOrderStatus.objects.default()
    #
    #     return super().build(template)


class SalesOrder(AbstractSalesOrder):
    class Meta(AbstractSalesOrder.Meta):
        swappable = 'BILLING_SALES_ORDER_MODEL'
