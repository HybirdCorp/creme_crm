# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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

from persons.workflow import transform_target_into_customer

from billing.constants import DEFAULT_DRAFT_INVOICE_STATUS
from billing.models import Invoice, InvoiceStatus
from billing.forms.base import BaseCreateForm, BaseEditForm


class InvoiceCreateForm(BaseCreateForm):
    class Meta:
        model = Invoice
        exclude = BaseCreateForm.Meta.exclude + ('number',)

    def __init__(self, *args, **kwargs):
        super(InvoiceCreateForm, self).__init__(*args, **kwargs)

        status_field = self.fields['status']
        queryset = InvoiceStatus.objects.filter(pk=DEFAULT_DRAFT_INVOICE_STATUS)

        status_field.queryset = queryset
        status_field.initial = queryset[0]

    def save(self, *args, **kwargs):
        instance = super(InvoiceCreateForm, self).save(*args, **kwargs)
        cleaned_data = self.cleaned_data
        transform_target_into_customer(cleaned_data['source'], cleaned_data['target'], instance.user)
        return instance


class InvoiceEditForm(BaseEditForm):
    class Meta:
        model = Invoice
        exclude = BaseEditForm.Meta.exclude + ('number',)

    def __init__(self, *args, **kwargs):
        super(InvoiceEditForm, self).__init__(*args, **kwargs)

        self.fields['status'].queryset = InvoiceStatus.objects.exclude(pk=DEFAULT_DRAFT_INVOICE_STATUS) if self.instance.number else \
                                         InvoiceStatus.objects.filter(pk=DEFAULT_DRAFT_INVOICE_STATUS)

