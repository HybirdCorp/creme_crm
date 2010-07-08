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

from django.contrib.contenttypes.models import ContentType

from creme_core.utils import create_or_update_models_instance as create
from creme_core.models.header_filter import HeaderFilterItem, HeaderFilter, HFI_FIELD
from creme_core.models import RelationType, SearchConfigItem, SearchField
from creme_core.management.commands.creme_populate import BasePopulator
from creme_core.utils.meta import get_verbose_field_name

from persons.models import Organisation

from billing.models import *
from billing.constants import *


class Populator(BasePopulator):
    dependencies = ['creme.creme_core', 'creme.persons']

    def populate(self, *args, **kwargs):
        RelationType.create((REL_SUB_BILL_ISSUED,   u"a été émis(e) par"), #[Invoice, Quote, SalesOrder]
                            (REL_OBJ_BILL_ISSUED,   u"a émis",             [Organisation]))
        RelationType.create((REL_SUB_BILL_RECEIVED, u"a été reçu(e) par"), #[Invoice, Quote, SalesOrder]
                            (REL_OBJ_BILL_RECEIVED, u"a reçu",             [Organisation]))


        #NB: pk=1 --> default status (used when a quote is converted in invoice for example)

        create(QuoteStatus, 1, name=u"En attente") #default status
        create(QuoteStatus, 2, name=u"Accepté")
        create(QuoteStatus, 3, name=u"Rejeté")
        create(QuoteStatus, 4, name=u"Créé")

        create(SalesOrderStatus, 1, name=u"Émis") #default status
        create(SalesOrderStatus, 2, name=u"Accepté")
        create(SalesOrderStatus, 3, name=u"Rejeté")
        create(SalesOrderStatus, 4, name=u"Créé")

        create(InvoiceStatus, 1, name=u"Brouillon") #default status
        create(InvoiceStatus, 2, name=u"Envoyée")
        create(InvoiceStatus, 3, name=u"Soldée")
        create(InvoiceStatus, 4, name=u"Partiellement soldée")
        create(InvoiceStatus, 5, name=u"Recouvrement")
        create(InvoiceStatus, 6, name=u"Recouvrement soldé")
        create(InvoiceStatus, 7, name=u"Annulée")

        get_ct = ContentType.objects.get_for_model

        def create_hf(hf_pk, hfi_pref, name, model):
            hf_id = create(HeaderFilter, hf_pk, name=name, entity_type_id=get_ct(model).id, is_custom=False).id
            create(HeaderFilterItem, hfi_pref + 'name',    order=1, name='name',            title=u'Nom',             type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, sortable=True, filter_string="name__icontains")
            create(HeaderFilterItem, hfi_pref + 'number',  order=2, name='number',          title=u'Numéro',          type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, sortable=True, filter_string="number__icontains")
            create(HeaderFilterItem, hfi_pref + 'issdate', order=3, name='issuing_date',    title=u"Date d'émission", type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, sortable=True, filter_string="issuing_date__range")
            create(HeaderFilterItem, hfi_pref + 'expdate', order=4, name='expiration_date', title=u"Date d'échéance", type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, sortable=True, filter_string="expiration_date__range")
            create(HeaderFilterItem, hfi_pref + 'status',  order=5, name='status',          title=u'Statut',          type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True, sortable=True, filter_string="status__name__icontains")

        create_hf('billing-hf_invoice',    'billing-hfi_invoice_',    'Vue de Facture',         Invoice)
        create_hf('billing-hf_quote',      'billing-hfi_quote_',      'Vue de Devis',           Quote)
        create_hf('billing-hf_salesorder', 'billing-hfi_salesorder_', 'Vue de Bon de Commande', SalesOrder)

        model = Invoice
        sci = create(SearchConfigItem, content_type_id=ContentType.objects.get_for_model(model).id)
        SCI_pk = sci.pk
        sci_fields = ['name', 'number', 'total', 'status__name']
        for i, field in enumerate(sci_fields):
            create(SearchField, field=field, field_verbose_name=get_verbose_field_name(model, field), order=i, search_config_item_id=SCI_pk)

        model = Quote
        sci = create(SearchConfigItem, content_type_id=ContentType.objects.get_for_model(model).id)
        SCI_pk = sci.pk
        sci_fields = ['name', 'number', 'total', 'status__name']
        for i, field in enumerate(sci_fields):
            create(SearchField, field=field, field_verbose_name=get_verbose_field_name(model, field), order=i, search_config_item_id=SCI_pk)

        model = SalesOrder
        sci = create(SearchConfigItem, content_type_id=ContentType.objects.get_for_model(model).id)
        SCI_pk = sci.pk
        sci_fields = ['name', 'number', 'total', 'status__name']
        for i, field in enumerate(sci_fields):
            create(SearchField, field=field, field_verbose_name=get_verbose_field_name(model, field), order=i, search_config_item_id=SCI_pk)