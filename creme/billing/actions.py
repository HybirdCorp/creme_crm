# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2018-2020  Hybird
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

from django.urls.base import reverse
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme import billing
from creme.creme_core.gui.actions import UIAction

Invoice = billing.get_invoice_model()
Quote   = billing.get_quote_model()


class ExportAction(UIAction):
    type = 'redirect'

    label = _('Download')
    icon = 'download'
    help_text = _('Download as PDF')

    @property
    def url(self):
        return reverse('billing__export', args=(self.instance.id,))

    @property
    def is_enabled(self):
        return self.user.has_perm_to_view(self.instance)


class ExportInvoiceAction(ExportAction):
    id = ExportAction.generate_id('billing', 'export_invoice')
    model = Invoice


class ExportQuoteAction(ExportAction):
    id = ExportAction.generate_id('billing', 'export_quote')
    model = Quote


class GenerateNumberAction(UIAction):
    id = UIAction.generate_id('billing', 'generate_number')
    type = 'billing-invoice-number'
    model = Invoice

    label = _('Invoice number')
    icon = 'invoice'
    help_text = _('Generate the number of the Invoice')

    @property
    def url(self):
        return reverse('billing__generate_invoice_number', args=(self.instance.id,))

    @property
    def is_enabled(self):
        return self.user.has_perm_to_change(self.instance) and not bool(self.instance.number)

    def _get_options(self):
        return {
            'confirm': gettext('Do you really want to generate an invoice number?'),
        }
