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
from billing.models.other_models import AdditionalInformation, PaymentTerms, PaymentInformation
from billing.utils import round_to_2


class Base(CremeEntity):
    name             = CharField(_(u'Name'), max_length=100)
    number           = CharField(_(u'Number'), max_length=100, blank=True, null=True)
    issuing_date     = DateField(_(u"Issuing date"), blank=True, null=True)
    expiration_date  = DateField(_(u"Expiration date"), blank=True, null=True) #TODO: null/blank=False (required in the form)
    discount         = DecimalField(_(u'Discount'), max_digits=4, decimal_places=2, blank=True, null=True)
    billing_address  = ForeignKey(Address, verbose_name=_(u'Billing address'), related_name='BillingAddress_set', blank=True, null=True)
    shipping_address = ForeignKey(Address, verbose_name=_(u'Shipping address'), related_name='ShippingAddress_set', blank=True, null=True)
    comment          = CharField(_(u'Comment'), max_length=500, blank=True, null=True)
    total_vat        = DecimalField(_(u'Total with VAT'),    max_digits=14, decimal_places=2, blank=True, null=True, editable=False, default=0)
    total_no_vat     = DecimalField(_(u'Total without VAT'), max_digits=14, decimal_places=2, blank=True, null=True, editable=False, default=0)
    additional_info  = ForeignKey(AdditionalInformation, verbose_name=_(u'Additional Information'), related_name='AdditionalInformation_set', blank=True, null=True)
    payment_terms    = ForeignKey(PaymentTerms,          verbose_name=_(u'Payment Terms'),          related_name='PaymentTerms_set',          blank=True, null=True)
    payment_info     = ForeignKey(PaymentInformation, verbose_name=_(u'Payment information'), blank=True, null=True, editable=False)

    research_fields = CremeEntity.research_fields + ['name']
    excluded_fields_in_html_output = CremeEntity.excluded_fields_in_html_output + ['total_vat', 'total_no_vat', 'payment_info']

    generate_number_in_create = True

    class Meta:
        app_label = 'billing'

    def __init__(self, *args, **kwargs):
        super(Base, self).__init__(*args, **kwargs)
        self._productlines_cache = None
        self._servicelines_cache = None

    def __unicode__(self):
        return self.name

    def invalidate_cache(self):
        self._productlines_cache = None
        self._servicelines_cache = None

    def save(self, *args, **kwargs):
        self.total_vat    = self.get_total_with_tax()
        self.total_no_vat = self.get_total()
        return super(Base, self).save(*args, **kwargs)

    #TODO: factorise with get_target()
    #TODO: return an Organisation instead of a CremeEntity ?? <- If doing this check calls to .get_source().get_real_entity()
    def get_source(self):
        try:
            return Relation.objects.get(subject_entity=self, type=REL_SUB_BILL_ISSUED).object_entity if self.id else None
        except Relation.DoesNotExist:
            return None

    def get_target(self):
        try:
            return Relation.objects.get(subject_entity=self, type=REL_SUB_BILL_RECEIVED).object_entity if self.id else None
        except Relation.DoesNotExist:
            return None

    #TODO: use get_source/get_target
    def populate_with_organisation(self):
        relations_getter = Relation.objects.get
        try:
            self.source = relations_getter(subject_entity=self, type=REL_SUB_BILL_ISSUED).object_entity if self.id else None
            self.target = relations_getter(subject_entity=self, type=REL_SUB_BILL_RECEIVED).object_entity if self.id else None
        except Relation.DoesNotExist:
            self.source = None
            self.target = None

    def generate_number(self, source=None):
        from billing.registry import algo_registry #lazy loading of number generators

        if source is None:
            source = self.get_source()
        self.number = 0

        if source:
            real_content_type = self.entity_type

            try:
                name_algo = ConfigBillingAlgo.objects.get(organisation=source, ct=real_content_type).name_algo
                algo = algo_registry.get_algo(name_algo)
                self.number = algo().generate_number(source, real_content_type)
            except Exception, e:
                debug('Exception during billing.generate_number(): %s', e)

    @property
    def product_lines(self):
        if self._productlines_cache is None:
             #force the retrieving all all lines (no slice)
            self._productlines_cache = list(ProductLine.objects.filter(document=self.id)) #NB: 'document=self.id' instead of 'document=self' avoids a weird query
        else:
            debug('Cache HIT for product lines in document pk=%s !!' % self.id)

        return self._productlines_cache

    @property
    def service_lines(self):
        if self._servicelines_cache is None:
            self._servicelines_cache = list(ServiceLine.objects.filter(document=self.id))
        else:
            debug('Cache HIT for service lines in document pk=%s !!' % self.id)

        return self._servicelines_cache

    # Could replace get_x_lines()
    def get_lines(self, klass):
        return klass.objects.filter(document=self)

    def get_product_lines_total_price_exclusive_of_tax(self):
        return round_to_2(sum(l.get_price_exclusive_of_tax() for l in self.product_lines))

    def get_product_lines_total_price_inclusive_of_tax(self):
        return round_to_2(sum(l.get_price_inclusive_of_tax() for l in self.product_lines))

    def get_service_lines_total_price_exclusive_of_tax(self):
        return round_to_2(sum(l.get_price_exclusive_of_tax() for l in self.service_lines))

    def get_service_lines_total_price_inclusive_of_tax(self):
        return round_to_2(sum(l.get_price_inclusive_of_tax() for l in self.service_lines))

    def get_total(self):
        return self.get_service_lines_total_price_exclusive_of_tax() + self.get_product_lines_total_price_exclusive_of_tax()

    def get_total_with_tax(self):
        return self.get_service_lines_total_price_inclusive_of_tax() + self.get_product_lines_total_price_inclusive_of_tax()

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
        source = get_relation(subject_entity=template, type=REL_SUB_BILL_ISSUED).object_entity
        target = get_relation(subject_entity=template, type=REL_SUB_BILL_RECEIVED).object_entity

        create_relation = Relation.objects.create
        create_relation(subject_entity=self, type_id=REL_SUB_BILL_ISSUED,   object_entity=source, user=self.user)
        create_relation(subject_entity=self, type_id=REL_SUB_BILL_RECEIVED, object_entity=target, user=self.user)

    def _build_properties(self, template):
        debug("=> Clone properties")
        # TODO...
