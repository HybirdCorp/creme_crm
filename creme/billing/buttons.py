# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

from django.utils.translation import ugettext_lazy as _

from creme_core.gui.button_menu import Button


class GenerateInvoiceNumberyButton(Button):
    id_           = Button.generate_id('billing', 'generate_invoice_number')
    verbose_name  = _(u'Generate the number of the Invoice')
    template_name = 'billing/templatetags/button_generate_invoice_number.html'

    def get_ctypes(self):
        from billing.models import Invoice
        return (Invoice,)

    def ok_4_display(self, entity):
        return not bool(entity.number)


generate_invoice_number_button = GenerateInvoiceNumberyButton()
