# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2012  Hybird
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

from billing.models import Invoice
from billing.forms.base import BaseCreateForm, BaseEditForm


class InvoiceCreateForm(BaseCreateForm):
    class Meta(BaseCreateForm.Meta):
        model = Invoice

    def save(self, *args, **kwargs):
        instance = super(InvoiceCreateForm, self).save(*args, **kwargs)
        cleaned_data = self.cleaned_data
        transform_target_into_customer(cleaned_data['source'], cleaned_data['target'], instance.user)
        return instance


class InvoiceEditForm(BaseEditForm):
    class Meta(BaseEditForm.Meta):
        model = Invoice

