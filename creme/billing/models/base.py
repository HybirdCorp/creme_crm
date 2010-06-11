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

from logging import debug

from django.db.models import CharField, ForeignKey, DateField, DecimalField
from django.utils.translation import ugettext_lazy as _

from creme_core.models import CremeEntity, Relation

from persons.models import Address

from product_line import ProductLine
from service_line import ServiceLine
from algo import ConfigBillingAlgo
from billing.constants import REL_SUB_BILL_ISSUED, REL_SUB_BILL_RECEIVED
from billing.utils import round_to_2
from billing.registry import algo_registry


class Base(CremeEntity):
    name             = CharField(_(u'Nom'), max_length=100, blank=False, null=False)
    number           = CharField(_(u'Numéro'), max_length=100, blank=True, null=True)
    issuing_date     = DateField(_(u"Date d'émission"), blank=True, null=True)
    expiration_date  = DateField(_(u"Date d'échéance"), blank=True, null=True)
    discount         = DecimalField(_(u'Remise'), max_digits=4, decimal_places=2, blank=True, null=True)
    billing_address  = ForeignKey(Address, verbose_name=_(u'Adresse de facturation'), related_name='BillingAddress_set',blank=True, null=True)
    shipping_address = ForeignKey(Address, verbose_name=_(u'Adresse de livraison'), related_name='ShippingAddress_set',blank=True, null=True)
    comment          = CharField(_(u'Remarques'), max_length=500, blank=True, null=True)
    total            = DecimalField(_(u'Total'), max_digits=14, decimal_places=2, blank=True, null=True)

    research_fields = CremeEntity.research_fields + ['name']

    class Meta:
        app_label = 'billing'

    def __unicode__(self):
        return self.name

    def get_source (self):
        relations_getter = Relation.objects.get
        try:
            return relations_getter(subject_id=self.id, type=REL_SUB_BILL_ISSUED).object_creme_entity if self.id else None
        except Relation.DoesNotExist:
            return None

    def get_target (self):
        relations_getter = Relation.objects.get
        try:
            return relations_getter(subject_id=self.id, type=REL_SUB_BILL_RECEIVED).object_creme_entity if self.id else None
        except Relation.DoesNotExist:
            return None

    def populate_with_organisation(self):
        relations_getter = Relation.objects.get
        try:
            self.source = relations_getter(subject_id=self.id, type=REL_SUB_BILL_ISSUED).object_creme_entity if self.id else None
            self.target = relations_getter(subject_id=self.id, type=REL_SUB_BILL_RECEIVED).object_creme_entity if self.id else None
        except Relation.DoesNotExist:
            self.source = None
            self.target = None

    def generate_number(self):
        source = self.get_source ()
        real_content_type = self.entity_type
        self.number = 0 
        if source :
            try : 
                name_algo = ConfigBillingAlgo.objects.get ( organisation=source, ct=real_content_type).name_algo
                print name_algo 
                algo = algo_registry.get_algo(name_algo)
                number = algo().generate_number (source, real_content_type)
                self.number =  number 
            except :
                pass
              
        self.save ()

    def get_product_lines(self):
        return ProductLine.objects.filter(document=self)

    def get_service_lines(self):
        return ServiceLine.objects.filter(document=self)

    # Could replace get_x_lines()
    def get_lines(self, klass):
        return klass.objects.filter(document=self)

    # TODO : Not use and could be refactor : get_line_total_price(tax = True, klass) ( klass would be ProductLine, ServiceLine, ... )
    def get_product_lines_total_price_exclusive_of_tax(self):
        total = 0
        for p in ProductLine.objects.filter(document=self):
            total += p.get_price_exclusive_of_tax()
        return round_to_2(total)

    def get_product_lines_total_price_inclusive_of_tax(self):
        total = 0
        for p in ProductLine.objects.filter(document=self):
            total += p.get_price_inclusive_of_tax()
        return round_to_2(total)


    def get_service_lines_total_price_exclusive_of_tax(self):
        total = 0
        for s in ServiceLine.objects.filter(document=self):
            total += s.get_price_exclusive_of_tax()
        return round_to_2(total)

    def get_service_lines_total_price_inclusive_of_tax(self):
        total = 0
        for s in ServiceLine.objects.filter(document=self):
            total += s.get_price_inclusive_of_tax()
        return round_to_2(total)
    
    def get_total (self):
        return self.get_service_lines_total_price_exclusive_of_tax () + self.get_product_lines_total_price_exclusive_of_tax()

    def get_total_with_tax(self):
        return self.get_service_lines_total_price_inclusive_of_tax () + self.get_product_lines_total_price_inclusive_of_tax()

    def build(self, template):
        self._build_object(template)
        self._build_lines(template, ProductLine)
        self._build_lines(template, ServiceLine)
        self._build_relations( template)
        self._build_properties(template)

    def _build_object(self, template):
        debug("=> Clone base object")
        self.user               = template.user
        self.name               = template.name
        self.number             = template.number
        self.issuing_date       = template.issuing_date
        self.expiration_date    = template.expiration_date
        self.discount           = template.discount
        self.billing_address    = template.billing_address
        self.shipping_address   = template.shipping_address
        self.comment            = template.comment
        self.total              = template.total
        self.save()

    def _build_lines(self, template, klass):
        debug("=> Clone lines")
        for line in template.get_lines(klass):
            cloned_line = line.clone()
            cloned_line.document = self
            cloned_line.save()

    def _build_relations(self, template):
        debug("=> Clone relations")
        # TODO : method clones only actors relations of the base object...should clone all others...
        get_relation = Relation.objects.get
        source = get_relation(subject_id=template.id, type=REL_SUB_BILL_ISSUED).object_creme_entity
        target = get_relation(subject_id=template.id, type=REL_SUB_BILL_RECEIVED).object_creme_entity

        create_relation = Relation.create_relation_with_object
        create_relation(self, REL_SUB_BILL_ISSUED,   source)
        create_relation(self, REL_SUB_BILL_RECEIVED, target)

    def _build_properties(self, template):
        debug("=> Clone properties")
        # TODO...
        