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

from django.forms import ModelChoiceField
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext_lazy as _

#from creme_core.forms import CremeModelForm

from billing.models import Invoice, InvoiceStatus, TemplateBase
from base import BaseCreateForm, BaseEditForm
from templatebase import TemplateBaseCreateForm


#class InvoiceListViewForm(CremeModelForm):
    #class Meta:
        #model = Invoice


class InvoiceCreateForm(BaseCreateForm):
    class Meta:
        model = Invoice
        exclude = BaseCreateForm.exclude + ('number',)

    #def save(self):
        #if self.is_valid() :
            #instance = super(InvoiceCreateForm, self).save()

            #organisation_source = instance.organisation_source

            ##TODO: remove me !!!!!!!!!!!!!!!!!!!!!!!!!!!!
            #exec("from creme_config.utils import %s as id_gen_func" % organisation_source.algo_factu.nom)
            #instance.numero_facture = id_gen_func(organisation_source)

            #instance.save()

            #self.save_lines()

class InvoiceEditForm(BaseEditForm):
    class Meta:
        model = Invoice
        exclude = BaseEditForm.exclude + ('number',)
