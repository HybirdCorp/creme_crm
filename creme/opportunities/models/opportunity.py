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

from itertools import chain
from logging import error

from django.db.models import CharField, TextField, ForeignKey, PositiveIntegerField, DateField
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType

from creme_core.models import CremeEntity, CremeModel, Relation, FunctionField

from creme_config.models import SettingValue

from persons.models import Contact, Organisation

from products.models import Product, Service

from billing.models import Invoice, SalesOrder, Quote, ProductLine, ServiceLine
from billing.utils import round_to_2

from opportunities.constants import *


class _TurnoverField(FunctionField):
    name         = "get_weighted_sales"
    verbose_name = _(u"Weighted sales")


class SalesPhase(CremeModel):
    name        = CharField(_(u"Name"), max_length=100, blank=False, null=False)
    description = TextField(_(u"Description"))

    def __unicode__(self):
        return self.name

    class Meta:
        app_label = "opportunities"
        verbose_name = _(u"Sale phase")
        verbose_name_plural = _(u'Sale phases')


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
    name            = CharField(_(u"Name of the opportunity"), max_length=100, blank=False, null=False)
    reference       = CharField(_(u"Reference"), max_length=100, blank=True, null=True)
    estimated_sales = PositiveIntegerField(_(u'Estimated sales'), blank=True, null=True)
    made_sales      = PositiveIntegerField(_(u'Made sales'), blank=True, null=True)
    sales_phase     = ForeignKey(SalesPhase, verbose_name=_(u'Sales phase'))
    chance_to_win   = PositiveIntegerField(_(ur"% of chance to win"), blank=True, null=True)
    closing_date    = DateField(_(u'Closing date'), blank=False, null=False)
    origin          = ForeignKey(Origin, verbose_name=_(u'Origin'), blank=True, null=True)
    description     = TextField(_(u'Description'), blank=True, null=True)

    function_fields = CremeEntity.function_fields.new(_TurnoverField)

    _use_lines     = None
    _product_lines = None
    _service_lines = None

    class Meta:
        app_label = "opportunities"
        verbose_name = _(u'Opportunity')
        verbose_name_plural = _(u'Opportunities')

    def __init__(self, *args, **kwargs):
        super(Opportunity, self).__init__(*args, **kwargs)

        self._linked_activities = None

    def __unicode__(self):
        return self.name

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
    def use_lines(self):
        if self._use_lines is None:
            self._use_lines = SettingValue.objects.get(key=SETTING_USE_LINES).value
        return self._use_lines

    @property
    def product_lines(self):
        if self._product_lines is None:
            self._product_lines = ProductLine.objects.filter(document=self)
        return self._product_lines

    @property
    def service_lines(self):
        if self._service_lines is None:
            self._service_lines = ServiceLine.objects.filter(document=self)
        return self._service_lines

    #TODO: factorise with billing ??
    def get_total(self):
        if self.use_lines:
            #TODO: can use aggregate functions instead ???
            return round_to_2(sum(l.get_price_exclusive_of_tax() for l in chain(self.product_lines, self.service_lines)))
        else:
            if self.made_sales:
                return self.made_sales
            else:
                return (self.estimated_sales or 0.0)

    #TODO: factorise with billing ??
    def get_total_with_tax(self):
        if self.use_lines:
            return round_to_2(sum(l.get_price_inclusive_of_tax() for l in chain(self.product_lines, self.service_lines)))
        else:
            tax = 1.196 #TODO: use constant or setting ?

            if self.made_sales:
                return self.made_sales * tax
            else:
                return (self.estimated_sales or 0) * tax

    def get_quotes(self):
        return Quote.objects.filter(relations__object_entity=self.id, relations__type=REL_SUB_LINKED_QUOTE)

    def get_current_quote_id(self):
        ct        = ContentType.objects.get_for_model(Quote)
        quote_ids = Relation.objects.filter(object_entity=self.id, type=REL_SUB_CURRENT_DOC, subject_entity__entity_type=ct) \
                                    .values_list('subject_entity_id', flat=True)

        if len(quote_ids) > 1:
            error('Several current quotes for opportunity: %s', self)

        return quote_ids[0] if quote_ids else None

    def get_target_orga(self):
        #NB: this one generates 2 queries instead of one Organisation.objects.get(relations__object_entity=SELF, ...) !!
        return Organisation.objects.get(relations__object_entity=self.id, relations__type=REL_OBJ_TARGETS_ORGA)

    def get_emit_orga(self):
        return Organisation.objects.get(relations__object_entity=self.id, relations__type=REL_SUB_EMIT_ORGA)

    def get_products(self):
        return Product.objects.filter(relations__object_entity=self.id, relations__type=REL_SUB_LINKED_PRODUCT)

    def get_services(self):
        return Service.objects.filter(relations__object_entity=self.id, relations__type=REL_SUB_LINKED_SERVICE)

    def get_contacts(self):
        return Contact.objects.filter(relations__object_entity=self.id, relations__type=REL_SUB_LINKED_CONTACT)

    def get_responsibles(self):
        return Contact.objects.filter(relations__object_entity=self.id, relations__type=REL_SUB_RESPONSIBLE)

    def get_salesorder(self):
        return SalesOrder.objects.filter(relations__object_entity=self.id, relations__type=REL_SUB_LINKED_SALESORDER)

    def get_invoices(self):
        return Invoice.objects.filter(relations__object_entity=self.id, relations__type=REL_SUB_LINKED_INVOICE)

    def link_to_target_orga(self, orga):
        Relation.objects.create(subject_entity=orga, type_id=REL_OBJ_TARGETS_ORGA,
                                object_entity=self, user=self.user
                               )

    def link_to_emit_orga(self, orga):
        Relation.objects.create(subject_entity=orga, type_id=REL_SUB_EMIT_ORGA,
                                object_entity=self, user=self.user
                               )
