# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2016  Hybird
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

from collections import defaultdict
import datetime
# from decimal import Decimal

# from django.db.models import Sum
from django.utils.translation import ugettext_lazy as _, ugettext

from creme.creme_core.core.function_field import FunctionField, FunctionFieldDecimal
from creme.creme_core.models import Relation, FieldsConfig

from creme.persons import get_contact_model, get_organisation_model

from . import get_invoice_model, get_quote_model
from .constants import REL_SUB_BILL_RECEIVED, REL_OBJ_BILL_ISSUED  # REL_OBJ_BILL_RECEIVED


Contact      = get_contact_model()
Organisation = get_organisation_model()

Invoice = get_invoice_model()
Quote   = get_quote_model()


# OLD VERSION
# def sum_totals_no_vat(model, entity, **kwargs):
#     billings = entity.relations.filter(type=REL_OBJ_BILL_RECEIVED).values_list('object_entity', flat=True)
#
#     creme_orgas_billings_ids = []
#     for orga in Organisation.get_all_managed_by_creme():
#         creme_orgas_billings_ids.extend(orga.relations.filter(type=REL_OBJ_BILL_ISSUED,
#                                                               object_entity_id__in=billings,
#                                                              )
#                                                       .values_list('object_entity', flat=True))
#
#     billing_documents = model.objects.filter(id__in=creme_orgas_billings_ids,
#                                              is_deleted=False,
#                                              total_no_vat__isnull=False,
#                                              **kwargs)
#
#     return sum(billing_document.total_no_vat for billing_document in billing_documents)
# OLD VERSION with AGGREGATE()
# def sum_totals_no_vat(model, entity, **kwargs):
#     billings = entity.relations.filter(type=REL_OBJ_BILL_RECEIVED).values_list('object_entity', flat=True)
#
#     creme_orgas_billings_ids = []
#     for orga in Organisation.get_all_managed_by_creme():
#         creme_orgas_billings_ids.extend(orga.relations.filter(type=REL_OBJ_BILL_ISSUED,
#                                                               object_entity_id__in=billings,
#                                                              )
#                                                       .values_list('object_entity', flat=True))
#
#
#     total = model.objects.filter(id__in=creme_orgas_billings_ids,
#                                  is_deleted=False,
#                                  total_no_vat__isnull=False,
#                                  **kwargs) \
#                          .aggregate(sum_total=Sum('total_no_vat'))['sum_total']
#
#     return Decimal(0) if total is None else total
def sum_totals_no_vat(model, entity, **kwargs):
    all_totals = dict(model.objects.filter(relations__type=REL_SUB_BILL_RECEIVED,
                                           relations__object_entity=entity.id,
                                           is_deleted=False,
                                           total_no_vat__isnull=False,
                                           **kwargs
                                          )
                                   .values_list('id', 'total_no_vat')
                     )
    managed_ids = Relation.objects.filter(
            subject_entity__in=[o.id for o in Organisation.get_all_managed_by_creme()],
            type=REL_OBJ_BILL_ISSUED,
            object_entity_id__in=all_totals.keys(),
        ).values_list('object_entity', flat=True)

    return sum(all_totals[b_id] for b_id in managed_ids)


def sum_totals_no_vat_multi(model, entities, **kwargs):
    bill_info_map = defaultdict(list)
    bill_ids = []

    for bill_id, total, e_id in model.objects.filter(
                                    relations__type=REL_SUB_BILL_RECEIVED,
                                    relations__object_entity__in=[e.id for e in entities],
                                    is_deleted=False,
                                    total_no_vat__isnull=False,
                                    **kwargs
                                ).values_list('id', 'total_no_vat', 'relations__object_entity'):
        bill_info_map[e_id].append((bill_id, total))
        bill_ids.append(bill_id)

    managed_bill_ids = set(Relation.objects.filter(
                                subject_entity__in=[o.id for o in Organisation.get_all_managed_by_creme()],
                                type=REL_OBJ_BILL_ISSUED,
                                object_entity_id__in=bill_ids,
                          ).values_list('object_entity', flat=True))

    for entity in entities:
        yield entity, sum(total for bill_id, total in bill_info_map[entity.id]
                            if bill_id in managed_bill_ids
                         )


def get_total_pending(entity):
    return sum_totals_no_vat(Invoice, entity, status__pending_payment=True)


def get_total_pending_multi(entities):
    return sum_totals_no_vat_multi(Invoice, entities, status__pending_payment=True)

# def _get_quote_fieldsconfig(entity):
#     fc = getattr(entity, '_fconfig_quote_cache', None)
#
#     if fc is None:
#         entity._fconfig_quote_cache = fc = FieldsConfig.get_4_model(Quote)
#
#     return fc


def get_total_won_quote_last_year(entity):
    # if _get_quote_fieldsconfig(entity).is_fieldname_hidden('acceptation_date'):
    if FieldsConfig.get_4_model(Quote).is_fieldname_hidden('acceptation_date'):
        return ugettext(u'Error: «Acceptation date» is hidden')

    return sum_totals_no_vat(Quote, entity,
                             status__won=True,
                             acceptation_date__year=datetime.date.today().year - 1,
                            )


def get_total_won_quote_last_year_multi(entities):
    if FieldsConfig.get_4_model(Quote).is_fieldname_hidden('acceptation_date'):
        msg = ugettext(u'Error: «Acceptation date» is hidden')
        return ((entity, msg) for entity in entities)

    return sum_totals_no_vat_multi(Quote, entities,
                                   status__won=True,
                                   acceptation_date__year=datetime.date.today().year - 1,
                                  )


def get_total_won_quote_this_year(entity):
    # TODO: factorise (decorator in creme_core ?)
    # if _get_quote_fieldsconfig(entity).is_fieldname_hidden('acceptation_date'):
    if FieldsConfig.get_4_model(Quote).is_fieldname_hidden('acceptation_date'):
        return ugettext(u'Error: «Acceptation date» is hidden')

    return sum_totals_no_vat(Quote, entity,
                             status__won=True,
                             acceptation_date__year=datetime.date.today().year,
                            )


def get_total_won_quote_this_year_multi(entities):
    # TODO: factorise
    if FieldsConfig.get_4_model(Quote).is_fieldname_hidden('acceptation_date'):
        msg = ugettext(u'Error: «Acceptation date» is hidden')
        return ((entity, msg) for entity in entities)

    return sum_totals_no_vat_multi(Quote, entities,
                                   status__won=True,
                                   acceptation_date__year=datetime.date.today().year,
                                  )


# class _BaseTotalWonQuote(FunctionField):
#     result_type = FunctionFieldDecimal  # Useful to get the right CSS class in list-view
#
#     @classmethod
#     def populate_entities(cls, entities):
#         fc = FieldsConfig.get_4_model(Quote)
#
#         for entity in entities:
#             entity._fconfig_quote_cache = fc

class _BaseTotalFunctionField(FunctionField):
    result_type = FunctionFieldDecimal  # Useful to get the right CSS class in list-view
    cache_attr  = None  # OVERLOAD ME

    def __call__(self, entity):
        cache_attr = self.cache_attr
        total = getattr(entity, cache_attr, None)

        if total is None:
            total = self.single_func()(entity)
            setattr(entity, cache_attr, total)

        return FunctionFieldDecimal(total)

    @classmethod
    def populate_entities(cls, entities):
        cache_attr = cls.cache_attr

        for entity, total in cls.multi_func()(entities):
            setattr(entity, cache_attr, total)

    @classmethod
    def single_func(cls):
        raise NotImplementedError

    @classmethod
    def multi_func(cls):
        raise NotImplementedError


# class _TotalPendingPayment(FunctionField):
class _TotalPendingPayment(_BaseTotalFunctionField):
    name         = 'total_pending_payment'
    verbose_name = _(u'Total Pending Payment')
    # result_type  = FunctionFieldDecimal  # Useful to get the right CSS class in list-view
    cache_attr   = '_cached_billing_total_pending_payment'

    # def __call__(self, entity):
    #     return FunctionFieldDecimal(get_total_pending(entity))

    @classmethod
    def single_func(cls):
        return get_total_pending

    @classmethod
    def multi_func(cls):
        return get_total_pending_multi


# class _TotalWonQuoteThisYear(_BaseTotalWonQuote):
class _TotalWonQuoteThisYear(_BaseTotalFunctionField):
    name         = 'total_won_quote_this_year'
    verbose_name = _(u'Total Won Quote This Year')
    cache_attr   = '_cached_billing_total_won_quote_this_year'

    # def __call__(self, entity):
    #     return FunctionFieldDecimal(get_total_won_quote_this_year(entity))

    @classmethod
    def single_func(cls):
        return get_total_won_quote_this_year

    @classmethod
    def multi_func(cls):
        return get_total_won_quote_this_year_multi


# class _TotalWonQuoteLastYear(_BaseTotalWonQuote):
class _TotalWonQuoteLastYear(_BaseTotalFunctionField):
    name         = 'total_won_quote_last_year'
    verbose_name = _(u'Total Won Quote Last Year')
    cache_attr   = '_cached_billing_total_won_quote_last_year'

    # def __call__(self, entity):
    #     return FunctionFieldDecimal(get_total_won_quote_last_year(entity))

    @classmethod
    def single_func(cls):
        return get_total_won_quote_last_year

    @classmethod
    def multi_func(cls):
        return get_total_won_quote_last_year_multi


def hook_organisation():
    Organisation.function_fields.add(_TotalPendingPayment(),
                                     _TotalWonQuoteThisYear(),
                                     _TotalWonQuoteLastYear()
                                    )

    Contact.function_fields.add(_TotalPendingPayment(),
                                _TotalWonQuoteThisYear(),
                                _TotalWonQuoteLastYear()
                               )
