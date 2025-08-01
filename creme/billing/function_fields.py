################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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
import logging
from collections import defaultdict
from decimal import Decimal

from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme import billing, persons
from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.core.function_field import (
    FunctionField,
    FunctionFieldColorAndLabel,
    FunctionFieldDecimal,
    FunctionFieldResult,
)
from creme.creme_core.models import FieldsConfig, Relation

from .constants import REL_OBJ_BILL_ISSUED, REL_SUB_BILL_RECEIVED

logger = logging.getLogger(__name__)

Organisation = persons.get_organisation_model()

Invoice = billing.get_invoice_model()
Quote   = billing.get_quote_model()


class TemplateBaseVerboseStatusField(FunctionField):
    name = 'get_verbose_status'  # TODO: "billing-template_status"
    verbose_name = _('Status')
    result_type = FunctionFieldColorAndLabel

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # e.g. of item: Invoice: {UUID('123...'): InvoiceStatus(name='OK'), UUID(...): ...}
        self._statuses_per_model = defaultdict(dict)

    def __call__(self, entity, user):
        statuses_per_model = self._statuses_per_model
        statuses = statuses_per_model[entity.ct.model_class()]
        status_uuid = entity.status_uuid
        status = statuses.get(entity.status_uuid)

        if status is None:
            status_model = entity.ct.model_class()._meta.get_field('status').remote_field.model

            try:
                status = status_model.objects.get(uuid=status_uuid)
            except status_model.DoesNotExist as e:
                logger.warning('Invalid status in TemplateBase(id=%s) [%s]', entity.id, e)
                status = status_model(
                    uuid=status_uuid, name=_('? (Error in the Template, edit it to fix)'),
                )  # TODO: color='000000'?

            statuses[status_uuid] = status

        return self.result_type(label=status.name, color=status.color)

    def populate_entities(self, entities, user):
        statuses_per_model = self._statuses_per_model
        uuids_per_model = defaultdict(set)

        for tpl in entities:
            billing_model = tpl.ct.model_class()
            status_uuid = tpl.status_uuid
            if status_uuid not in statuses_per_model[billing_model]:
                uuids_per_model[billing_model].add(status_uuid)

        for billing_model, uuids in uuids_per_model.items():
            if uuids:
                status_model = billing_model._meta.get_field('status').remote_field.model
                statuses_per_model[billing_model].update(
                    (status.uuid, status) for status in status_model.objects.filter(uuid__in=uuids)
                )


def sum_totals_no_vat(model, entity, user, **kwargs) -> Decimal:
    all_totals = dict(
        EntityCredentials.filter(
            user,
            model.objects.filter(
                relations__type=REL_SUB_BILL_RECEIVED,
                relations__object_entity=entity.id,
                is_deleted=False,
                total_no_vat__isnull=False,
                **kwargs
            ).values_list('id', 'total_no_vat')
        )
    )
    managed_ids = Relation.objects.filter(
        subject_entity__in=[o.id for o in Organisation.objects.filter_managed_by_creme()],
        type=REL_OBJ_BILL_ISSUED,
        object_entity_id__in=all_totals.keys(),
    ).values_list('object_entity', flat=True)

    return sum(all_totals[b_id] for b_id in managed_ids)


def sum_totals_no_vat_multi(model, entities, user, **kwargs):
    bill_info_map = defaultdict(list)
    bill_ids = []

    for bill_id, total, e_id in EntityCredentials.filter(
        user,
        model.objects.filter(
            relations__type=REL_SUB_BILL_RECEIVED,
            relations__object_entity__in=[e.id for e in entities],
            is_deleted=False,
            total_no_vat__isnull=False,
            **kwargs
        ).values_list('id', 'total_no_vat', 'relations__object_entity')
    ):
        bill_info_map[e_id].append((bill_id, total))
        bill_ids.append(bill_id)

    managed_bill_ids = {
        *Relation.objects.filter(
            subject_entity__in=[
                # NB: not values_list() to use the cache of filter_managed_by_creme()
                o.id for o in Organisation.objects.filter_managed_by_creme()
            ],
            type=REL_OBJ_BILL_ISSUED,
            object_entity_id__in=bill_ids,
        ).values_list('object_entity', flat=True)
    }

    for entity in entities:
        yield (
            entity,
            sum(
                total
                for bill_id, total in bill_info_map[entity.id]
                if bill_id in managed_bill_ids
            )
        )


def get_total_pending(entity, user):
    return sum_totals_no_vat(Invoice, entity, user, status__pending_payment=True)


def get_total_pending_multi(entities, user):
    return sum_totals_no_vat_multi(Invoice, entities, user, status__pending_payment=True)


def get_total_won_quote_last_year(entity, user):
    if FieldsConfig.objects.get_for_model(Quote).is_fieldname_hidden('acceptation_date'):
        return gettext('Error: «Acceptation date» is hidden')

    return sum_totals_no_vat(
        Quote, entity, user,
        status__won=True,
        acceptation_date__year=datetime.date.today().year - 1,
    )


def get_total_won_quote_last_year_multi(entities, user):
    if FieldsConfig.objects.get_for_model(Quote).is_fieldname_hidden('acceptation_date'):
        msg = gettext('Error: «Acceptation date» is hidden')
        return ((entity, msg) for entity in entities)

    return sum_totals_no_vat_multi(
        Quote, entities, user,
        status__won=True,
        acceptation_date__year=datetime.date.today().year - 1,
    )


def get_total_won_quote_this_year(entity, user):
    # TODO: factorise (decorator in creme_core ?)
    if FieldsConfig.objects.get_for_model(Quote).is_fieldname_hidden('acceptation_date'):
        return gettext('Error: «Acceptation date» is hidden')

    return sum_totals_no_vat(
        Quote, entity, user,
        status__won=True,
        acceptation_date__year=datetime.date.today().year,
    )


def get_total_won_quote_this_year_multi(entities, user):
    # TODO: factorise
    if FieldsConfig.objects.get_for_model(Quote).is_fieldname_hidden('acceptation_date'):
        msg = gettext('Error: «Acceptation date» is hidden')
        return ((entity, msg) for entity in entities)

    return sum_totals_no_vat_multi(
        Quote, entities, user,
        status__won=True,
        acceptation_date__year=datetime.date.today().year,
    )


class _BaseTotalFunctionField(FunctionField):
    result_type = FunctionFieldDecimal  # Useful to get the right CSS class in list-view

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cache = defaultdict(dict)

    def __call__(self, entity, user):
        e_cache = self._cache[entity.id]
        total = e_cache.get(user.id)

        if total is None:
            total = e_cache[user.id] = self.single_func()(entity, user)

        return (
            FunctionFieldDecimal(total)
            if isinstance(total, Decimal) else
            FunctionFieldResult(total)
        )

    def populate_entities(self, entities, user):
        cache = self._cache
        user_id = user.id

        # TODO: only populate entities which are not already populated
        for entity, total in self.multi_func()(entities, user):
            cache[entity.id][user_id] = total

    @classmethod
    def single_func(cls):
        raise NotImplementedError

    @classmethod
    def multi_func(cls):
        raise NotImplementedError


# TODO: rename this class without '_' prefix ?
# TODO: prefix name with 'billing' (need data migration)
class _TotalPendingPayment(_BaseTotalFunctionField):
    name = 'total_pending_payment'
    verbose_name = _('Total pending payment')

    @classmethod
    def single_func(cls):
        return get_total_pending

    @classmethod
    def multi_func(cls):
        return get_total_pending_multi


class _TotalWonQuoteThisYear(_BaseTotalFunctionField):
    name = 'total_won_quote_this_year'
    verbose_name = _('Total won quotes this year')

    @classmethod
    def single_func(cls):
        return get_total_won_quote_this_year

    @classmethod
    def multi_func(cls):
        return get_total_won_quote_this_year_multi


class _TotalWonQuoteLastYear(_BaseTotalFunctionField):
    name = 'total_won_quote_last_year'
    verbose_name = _('Total won Quotes last Year')

    @classmethod
    def single_func(cls):
        return get_total_won_quote_last_year

    @classmethod
    def multi_func(cls):
        return get_total_won_quote_last_year_multi
