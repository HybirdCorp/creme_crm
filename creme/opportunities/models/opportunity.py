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

from logging import error, debug

from django.db.models import (CharField, TextField, ForeignKey, PositiveIntegerField,
                              DateField, PROTECT, SET_NULL)
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType

from creme_core.models import CremeEntity, CremeModel, Relation, Currency
from creme_core.constants import DEFAULT_CURRENCY_PK
from creme_core.core.function_field import FunctionField

from creme_config.models import SettingValue

from persons.models import Contact, Organisation

from products.models import Product, Service

from billing.models import Invoice, SalesOrder, Quote, Vat

from opportunities.constants import *


class _TurnoverField(FunctionField):
    name         = "get_weighted_sales"
    verbose_name = _(u"Weighted sales")


class SalesPhase(CremeModel):
    name        = CharField(_(u"Name"), max_length=100, blank=False, null=False)
    description = TextField(_(u"Description"))
    order       = PositiveIntegerField(_(u"Order"), default=1, editable=False)

    def __unicode__(self):
        return self.name

    class Meta:
        app_label = "opportunities"
        verbose_name = _(u"Sale phase")
        verbose_name_plural = _(u'Sale phases')
        ordering = ('order',)


class Origin(CremeModel):
    name        = CharField(_(u'Origin'), max_length=100, blank=False, null=False)
    description = TextField(_(u"Description"))

    def __unicode__(self):
        return self.name

    class Meta:
        app_label = "opportunities"
        verbose_name = _(u"Origin of opportunity")
        verbose_name_plural = _(u"Origins of opportunity")


class Opportunity(CremeEntity):
    name                  = CharField(_(u"Name of the opportunity"), max_length=100)
    reference             = CharField(_(u"Reference"), max_length=100, blank=True, null=True)
    estimated_sales       = PositiveIntegerField(_(u'Estimated sales'), blank=True, null=True)
    made_sales            = PositiveIntegerField(_(u'Made sales'), blank=True, null=True)
    currency              = ForeignKey(Currency, verbose_name=_(u'Currency'), default=DEFAULT_CURRENCY_PK, on_delete=PROTECT)
    sales_phase           = ForeignKey(SalesPhase, verbose_name=_(u'Sales phase'), on_delete=PROTECT)
    chance_to_win         = PositiveIntegerField(_(ur"% of chance to win"), blank=True, null=True)
    expected_closing_date = DateField(_(u'Expected closing date'), blank=True, null=True)
    closing_date          = DateField(_(u'Actual closing date'), blank=True, null=True)
    origin                = ForeignKey(Origin, verbose_name=_(u'Origin'), blank=True, null=True, on_delete=SET_NULL)
    description           = TextField(_(u'Description'), blank=True, null=True)
    first_action_date     = DateField(_(u'Date of the first action'), blank=True, null=True)

    function_fields = CremeEntity.function_fields.new(_TurnoverField())

    _use_current_quote  = None
#    _product_lines      = None
#    _service_lines      = None

    class Meta:
        app_label = "opportunities"
        verbose_name = _(u'Opportunity')
        verbose_name_plural = _(u'Opportunities')

    def __init__(self, *args, **kwargs):
        super(Opportunity, self).__init__(*args, **kwargs)

        self._linked_activities = None

    def __unicode__(self):
        return self.name

    def _pre_delete(self):
        for relation in Relation.objects.filter(type__in=[REL_SUB_TARGETS],
                                                subject_entity=self):
            relation._delete_without_transaction()

    def get_absolute_url(self):
        return "/opportunities/opportunity/%s" % self.id

    def get_edit_absolute_url(self):
        return "/opportunities/opportunity/edit/%s" % self.id

    @staticmethod
    def get_lv_absolute_url():
        """url for list_view """
        return "/opportunities/opportunities"

    def get_weighted_sales(self):
        return (self.estimated_sales or 0) * (self.chance_to_win or 0) / 100.0

    @property
    def use_current_quote(self):
        if self._use_current_quote is None:
            try:
                self._use_current_quote = SettingValue.objects.get(key=SETTING_USE_CURRENT_QUOTE).value
            except Opportunity.DoesNotExist:
                debug("Populate opportunities is not loaded")
                self._use_current_quote = False
        return self._use_current_quote

    def get_total(self):
        if self.made_sales:
            return self.made_sales
        else:
            return (self.estimated_sales or 0)

    def get_total_with_tax(self):
        tax = 1 + Vat.get_default_vat().value / 100

        if self.made_sales:
            return self.made_sales * tax
        else:
            return (self.estimated_sales or 0) * tax

    def get_target(self):
        #NB: this one generates 2 queries instead of one Organisation.objects.get(relations__object_entity=SELF, ...) !!
        return CremeEntity.objects.get(relations__object_entity=self.id, relations__type=REL_OBJ_TARGETS).get_real_entity()

    def get_source(self):
        return Organisation.objects.get(relations__object_entity=self.id, relations__type=REL_SUB_EMIT_ORGA)

    def get_products(self):
        return Product.objects.filter(relations__object_entity=self.id, relations__type=REL_SUB_LINKED_PRODUCT)

    def get_services(self):
        return Service.objects.filter(relations__object_entity=self.id, relations__type=REL_SUB_LINKED_SERVICE)

    def get_contacts(self):
        return Contact.objects.filter(relations__object_entity=self.id, relations__type=REL_SUB_LINKED_CONTACT)

    def get_responsibles(self):
        return Contact.objects.filter(relations__object_entity=self.id, relations__type=REL_SUB_RESPONSIBLE)

    def get_quotes(self):
            return Quote.objects.filter(relations__object_entity=self.id, relations__type=REL_SUB_LINKED_QUOTE)

    def get_current_quote_id(self):
        ct        = ContentType.objects.get_for_model(Quote)
        quote_ids = Relation.objects.filter(object_entity=self.id,
            type=REL_SUB_CURRENT_DOC,
            subject_entity__entity_type=ct)\
        .values_list('subject_entity_id', flat=True)

        if len(quote_ids) > 1:
            error('Several current quotes for opportunity: %s', self)

        if quote_ids:
            current_quote = quote_ids[0]
        else:
            return None

        # TODO When unlink a quote in opp, the current quote relation should be unlink too
        is_current_quote_linked_to_opp = Relation.objects.filter(object_entity=self.id, type=REL_SUB_LINKED_QUOTE, subject_entity=current_quote).exists()

        return current_quote if is_current_quote_linked_to_opp else None

    def get_salesorder(self):
        return SalesOrder.objects.filter(relations__object_entity=self.id, relations__type=REL_SUB_LINKED_SALESORDER)

    def get_invoices(self):
        return Invoice.objects.filter(relations__object_entity=self.id, relations__type=REL_SUB_LINKED_INVOICE)

    def link_to_target(self, target):
        Relation.objects.create(subject_entity=target, type_id=REL_OBJ_TARGETS,
                                object_entity=self, user=self.user
                               )

    def link_to_emit_orga(self, orga):
        Relation.objects.create(subject_entity=orga, type_id=REL_SUB_EMIT_ORGA,
                                object_entity=self, user=self.user
                               )

    def update_estimated_sales(self, document):
        self.estimated_sales = document.total_no_vat
        self.save()
