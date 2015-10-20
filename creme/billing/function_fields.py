# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2015  Hybird
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

import datetime

from django.utils.translation import ugettext_lazy as _, ugettext

from creme.creme_core.core.function_field import FunctionField, FunctionFieldResult
from creme.creme_core.models import FieldsConfig

from creme.persons import get_contact_model, get_organisation_model
#from creme.persons.models import Organisation, Contact

from . import get_invoice_model, get_quote_model
from .constants import REL_OBJ_BILL_RECEIVED, REL_OBJ_BILL_ISSUED
#from .models import Invoice, Quote


Contact      = get_contact_model()
Organisation = get_organisation_model()

Invoice      = get_invoice_model()
Quote        = get_quote_model()


def sum_totals_no_vat(model, entity, **kwargs):
    billings = entity.relations.filter(type=REL_OBJ_BILL_RECEIVED).values_list('object_entity', flat=True)

    creme_orgas_billings_ids = []
    for orga in Organisation.get_all_managed_by_creme():
        creme_orgas_billings_ids.extend(orga.relations.filter(type=REL_OBJ_BILL_ISSUED, object_entity_id__in=billings)
                                                  .values_list('object_entity', flat=True))

    billing_documents = model.objects.filter(id__in=creme_orgas_billings_ids,
                                             is_deleted=False,
                                             total_no_vat__isnull=False,
                                             **kwargs)
    return sum(billing_document.total_no_vat for billing_document in billing_documents)

def get_total_pending(entity):
    return sum_totals_no_vat(Invoice, entity,
                             status__pending_payment=True)

# TODO: move to CremeEntity ? (see Opportunity too)
# TODO: remove when FieldsConfig cache has been added.
def _get_quote_fieldsconfig(entity):
    fc = getattr(entity, '_fconfig_quote_cache', None)

    if fc is None:
        entity._fconfig_quote_cache = fc = FieldsConfig.get_4_model(Quote)

    return fc

def get_total_won_quote_last_year(entity):
    if _get_quote_fieldsconfig(entity).is_fieldname_hidden('acceptation_date'):
        return ugettext(u'Error: «Acceptation date» is hidden')

    today_date = datetime.date.today()

    return sum_totals_no_vat(Quote, entity,
                             status__won=True,
                             acceptation_date__year=today_date.year - 1,
                            )


def get_total_won_quote_this_year(entity):
    # TODO: factorise (decorator ?)
    if _get_quote_fieldsconfig(entity).is_fieldname_hidden('acceptation_date'):
        return ugettext(u'Error: «Acceptation date» is hidden')

    today_date = datetime.date.today()

    return sum_totals_no_vat(Quote, entity,
                             status__won=True,
                             acceptation_date__year=today_date.year,
                            )


class _BaseTotalWonQuote(FunctionField):
    @classmethod
    def populate_entities(cls, entities):
        # TODO: remove when FieldsConfig cache has been added.
        fc = FieldsConfig.get_4_model(Quote)

        for entity in entities:
            entity._fconfig_quote_cache = fc


class _TotalPendingPayment(FunctionField):
    name         = "total_pending_payment"
    verbose_name = _(u"Total Pending Payment")

    def __call__(self, entity):
        return FunctionFieldResult(get_total_pending(entity))

    # TODO: use cache for creme_orgas_billings_ids + regroup queries
    # def populate_entities(cls, entities):
    #     pass


#class _TotalWonQuoteThisYear(FunctionField):
class _TotalWonQuoteThisYear(_BaseTotalWonQuote):
    name         = "total_won_quote_this_year"
    verbose_name = _(u"Total Won Quote This Year")

    def __call__(self, entity):
        return FunctionFieldResult(get_total_won_quote_this_year(entity))

    # TODO: see _TotalPendingPayment
    # def populate_entities(cls, entities):
    #     pass


#class _TotalWonQuoteLastYear(FunctionField):
class _TotalWonQuoteLastYear(_BaseTotalWonQuote):
    name         = "total_won_quote_last_year"
    verbose_name = _(u"Total Won Quote Last Year")

    def __call__(self, entity):
        return FunctionFieldResult(get_total_won_quote_last_year(entity))

    # TODO: see _TotalPendingPayment
    # def populate_entities(cls, entities):
    #     pass


def hook_organisation():
    Organisation.function_fields.add(_TotalPendingPayment(),
                                     _TotalWonQuoteThisYear(),
                                     _TotalWonQuoteLastYear()
                                    )

    Contact.function_fields.add(_TotalPendingPayment(),
                                _TotalWonQuoteThisYear(),
                                _TotalWonQuoteLastYear()
                               )
