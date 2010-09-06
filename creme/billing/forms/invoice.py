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

from billing.constants import DEFAULT_DRAFT_INVOICE_STATUS

from billing.models import Invoice
from base import BaseCreateForm, BaseEditForm

from billing.models import InvoiceStatus
class InvoiceCreateForm(BaseCreateForm):
    class Meta:
        model = Invoice
        exclude = BaseCreateForm.Meta.exclude + ('number',)

    def __init__(self, *args, **kwargs):
        super(InvoiceCreateForm, self).__init__(*args, **kwargs)

        fields = self.fields
        fields['status'].queryset = InvoiceStatus.objects.filter(pk=DEFAULT_DRAFT_INVOICE_STATUS)

class InvoiceEditForm(BaseEditForm):
    class Meta:
        model = Invoice
        exclude = BaseEditForm.Meta.exclude + ('number',)
        
    def __init__(self, *args, **kwargs):
        super(InvoiceEditForm, self).__init__(*args, **kwargs)

        fields = self.fields
        if not self.instance.number :
            fields['status'].queryset = InvoiceStatus.objects.filter(pk=DEFAULT_DRAFT_INVOICE_STATUS)
        else:
            fields['status'].queryset = InvoiceStatus.objects.exclude(pk=DEFAULT_DRAFT_INVOICE_STATUS)
