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

from logging import error

from django.db.models import CharField, TextField, ForeignKey, PositiveIntegerField, DateField
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType

from creme_core.models import CremeEntity, CremeModel, Relation

from creme_config.models import CremeKVConfig

from persons.models import Contact, Organisation

from documents.constants import REL_SUB_CURRENT_DOC

from products.models import Product, Service

from billing.models import Invoice, SalesOrder, Quote, ProductLine, ServiceLine
from billing.utils import round_to_2

from opportunities.constants import *


class SalesPhase(CremeModel):
    name        = CharField(_(u"Nom"), max_length=100, blank=False, null=False)
    description = TextField(_(u"Description"))

    def __unicode__(self):
        return self.name

    class Meta:
        app_label = "opportunities"
        verbose_name = _(u"Phase de vente")
        verbose_name_plural = _(u'Phases de vente')


class Origin(CremeModel):
    name        = CharField(_(u'Origine'), max_length=100, blank=False, null=False)
    description = TextField(_(u"Description"))

    def __unicode__(self):
        return self.name

    class Meta:
        app_label = "opportunities"
        verbose_name = _(u'Origine')
        verbose_name_plural = _(u'Origines')


class Opportunity(CremeEntity):
    name            = CharField(_(u"Nom de l'opportunité"), max_length=100, blank=False, null=False)
    reference       = CharField(_(u"Référence"), max_length=100, blank=True, null=True)
    estimated_sales = PositiveIntegerField(_(u'CA estimé'), blank=True, null=True)
    made_sales      = PositiveIntegerField(_(u'CA final'), blank=True, null=True)
    sales_phase     = ForeignKey(SalesPhase, verbose_name=_(u'Phase de vente'))
    chance_to_win   = PositiveIntegerField(_(u"% de chance d'obtention"), blank=True, null=True)
    expiration_date = DateField(_(u'Échéance'), blank=False, null=False)
    origin          = ForeignKey(Origin, verbose_name=_(u'Origine'))

    users_allowed_func = CremeEntity.users_allowed_func + [{'name': 'get_weighted_sales', 'verbose_name': u'CA pondéré'}] #_(u'CA pondéré')

    class Meta:
        app_label = "opportunities"
        verbose_name = _(u'Opportunité')
        verbose_name_plural = _(u'Opportunités')

    def __init__(self, *args, **kwargs):
        super(Opportunity, self).__init__(*args, **kwargs)

        self._linked_activities = None

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return "/opportunities/opportunity/%s" % self.id

    def get_edit_absolute_url(self):
        return "/opportunities/opportunity/edit/%s" % self.id

    def get_delete_absolute_url(self):
        return "/opportunities/opportunity/delete/%s" % self.id

    @staticmethod
    def get_lv_absolute_url():
        """url for list_view """
        return "/opportunities/opportunities"

    def get_weighted_sales(self):
        return (self.estimated_sales or 0) * (self.chance_to_win or 0) / 100.0

    #TODO: 'cache' for ProductLines/ServiceLines ??
    def get_total(self):
        line_or_not = CremeKVConfig.objects.get(id="LINE_IN_OPPORTUNITIES").value
        if line_or_not == "1" :
            total = 0
            for s in ProductLine.objects.filter(document=self): #TODO: use sum()
                total += s.get_price_exclusive_of_tax()
            for s in ServiceLine.objects.filter(document=self):
                total += s.get_price_exclusive_of_tax()
            return round_to_2(total)
        else:
            if self.made_sales :
                return self.made_sales
            else:
                return (self.estimated_sales or 0)

    #TODO: factorise with get_total() ?
    def get_total_with_tax(self):
        line_or_not = CremeKVConfig.objects.get(id="LINE_IN_OPPORTUNITIES").value
        if line_or_not == "1":
            total = 0
            for s in ProductLine.objects.filter(document=self):
                total += s.get_price_inclusive_of_tax()
            for s in ServiceLine.objects.filter(document=self):
                total += s.get_price_inclusive_of_tax()
            return round_to_2(total)
        else:
            tax = 1.196

            if self.made_sales:
                return self.made_sales * tax
            else:
                return (self.estimated_sales or 0) * tax

    def get_quotes(self):
        return Quote.objects.filter(relations__object_entity=self, relations__type__id=REL_SUB_LINKED_QUOTE)

    def get_current_quote_id(self):
        ct        = ContentType.objects.get_for_model(Quote)
        quote_ids = Relation.objects.filter(object_entity=self, type__id=REL_SUB_CURRENT_DOC, subject_entity__entity_type=ct).values_list('subject_entity_id', flat=True)

        if len(quote_ids) > 1:
            error('Several current quotes for opportunity: %s', self)

        return quote_ids[0] if quote_ids else None

    def get_target_orga(self):
        return Organisation.objects.get(relations__object_entity=self, relations__type__id=REL_OBJ_TARGETS_ORGA)

    def get_emit_orga(self):
        #return Relation.objects.get(subject_entity=self, type__id=REL_OBJ_EMIT_ORGA).object_entity
        return Organisation.objects.get(relations__object_entity=self, relations__type__id=REL_SUB_EMIT_ORGA)

    def get_products(self):
        return Product.objects.filter(relations__object_entity=self, relations__type__id=REL_SUB_LINKED_PRODUCT)

    def get_services(self):
        return Service.objects.filter(relations__object_entity=self, relations__type__id=REL_SUB_LINKED_SERVICE)

    def get_contacts(self):
        return Contact.objects.filter(relations__object_entity=self, relations__type__id=REL_SUB_LINKED_CONTACT)

    def get_responsibles(self):
        return Contact.objects.filter(relations__object_entity=self, relations__type__id=REL_SUB_RESPONSIBLE)

    def get_salesorder(self):
        return SalesOrder.objects.filter(relations__object_entity=self, relations__type__id=REL_SUB_LINKED_SALESORDER)

    def get_invoices(self):
        return Invoice.objects.filter(relations__object_entity=self, relations__type__id=REL_SUB_LINKED_INVOICE)

    def link_to_target_orga(self, orga):
        Relation.create(orga, REL_OBJ_TARGETS_ORGA, self)

    def link_to_emit_orga(self, orga):
        Relation.create(orga, REL_SUB_EMIT_ORGA, self)
