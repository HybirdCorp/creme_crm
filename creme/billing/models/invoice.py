################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2024  Hybird
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

import logging

from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

# from creme.persons.workflow import transform_target_into_customer
from creme.creme_core.models import deletion

from .. import get_template_base_model
from ..constants import DEFAULT_DECIMAL
from .base import Base
from .other_models import InvoiceStatus

logger = logging.getLogger(__name__)


class AbstractInvoice(Base):
    status = models.ForeignKey(
        InvoiceStatus,
        verbose_name=_('Status of invoice'),
        on_delete=deletion.CREME_REPLACE,
    )
    buyers_order_number = models.CharField(
        _("Buyer's order"),
        max_length=100, blank=True,
        help_text=_("Number of buyer's order (french legislation)")
    ).set_tags(optional=True)

    creation_label = _('Create an invoice')
    save_label     = _('Save the invoice')

    search_score = 52

    generate_number_in_create = False

    class Meta(Base.Meta):
        abstract = True
        verbose_name = _('Invoice')
        verbose_name_plural = _('Invoices')

    def _pre_save_clone(self, source):
        super()._pre_save_clone(source=source)

        # TODO: <.set_tags(clonable=False)> + default in FK?
        status = InvoiceStatus.objects.filter(is_default=True).first()
        if status:
            self.status = status
        else:
            logger.critical('AbstractInvoice._pre_save_clone(): cannot find a default status')

        # TODO: what about "issuing_date"? should we copy it?

    def _get_total(self):
        lines_total, creditnotes_total = self._get_lines_total_n_creditnotes_total()

        if lines_total < 0 or creditnotes_total < lines_total:
            return lines_total - creditnotes_total

        return DEFAULT_DECIMAL

    def _get_total_with_tax(self):
        lines_total_with_tax, creditnotes_total = \
            self._get_lines_total_n_creditnotes_total_with_tax()

        if lines_total_with_tax < 0 or creditnotes_total < lines_total_with_tax:
            return lines_total_with_tax - creditnotes_total

        return DEFAULT_DECIMAL

    def get_absolute_url(self):
        return reverse('billing__view_invoice', args=(self.id,))

    @staticmethod
    def get_create_absolute_url():
        return reverse('billing__create_invoice')

    def get_edit_absolute_url(self):
        return reverse('billing__edit_invoice', args=(self.id,))

    @staticmethod
    def get_lv_absolute_url():
        return reverse('billing__list_invoices')

    def build(self, template):
        # Specific recurrent generation rules
        # status_id = 1
        status_id = None

        if isinstance(template, get_template_base_model()):
            tpl_status_id = template.status_id
            if InvoiceStatus.objects.filter(pk=tpl_status_id).exists():
                status_id = tpl_status_id

        # self.status_id = status_id
        if status_id:
            self.status_id = status_id
        else:
            self.status = InvoiceStatus.objects.filter(is_default=True).first()

        super().build(template)
        # transform_target_into_customer(self.source, self.target, self.user)

        return self


class Invoice(AbstractInvoice):
    class Meta(AbstractInvoice.Meta):
        swappable = 'BILLING_INVOICE_MODEL'
