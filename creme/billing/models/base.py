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

from decimal import Decimal

from itertools import chain
from logging import debug

from django.db.models import CharField, TextField, ForeignKey, DateField, DecimalField, SET_NULL, PROTECT
from django.utils.translation import ugettext_lazy as _

from creme_core.models import CremeEntity, Relation, Currency
from creme_core.constants import DEFAULT_CURRENCY_PK

from persons.models import Address

from line import Line
from product_line import ProductLine
from service_line import ServiceLine
from algo import ConfigBillingAlgo
from billing.constants import REL_SUB_BILL_ISSUED, REL_SUB_BILL_RECEIVED, REL_SUB_HAS_LINE, REL_OBJ_LINE_RELATED_ITEM, REL_OBJ_CREDIT_NOTE_APPLIED
from billing.models.other_models import AdditionalInformation, PaymentTerms, PaymentInformation
from billing.utils import round_to_2


default_decimal = Decimal()

class Base(CremeEntity):
    name             = CharField(_(u'Name'), max_length=100)
    number           = CharField(_(u'Number'), max_length=100, blank=True, null=True, editable=False)
    issuing_date     = DateField(_(u"Issuing date"), blank=True, null=True)
    expiration_date  = DateField(_(u"Expiration date"), blank=True, null=True) # TODO blank, null = False, required in form
    discount         = DecimalField(_(u'Overall discount'), max_digits=10, decimal_places=2, default=default_decimal)
    billing_address  = ForeignKey(Address, verbose_name=_(u'Billing address'), related_name='BillingAddress_set', blank=True, null=True)
    shipping_address = ForeignKey(Address, verbose_name=_(u'Shipping address'), related_name='ShippingAddress_set', blank=True, null=True)
    currency         = ForeignKey(Currency, verbose_name=_(u'Currency'), related_name='Currency_set', default=DEFAULT_CURRENCY_PK, on_delete=PROTECT)
    comment          = TextField(_(u'Comment'), blank=True, null=True)
    total_vat        = DecimalField(_(u'Total with VAT'),    max_digits=14, decimal_places=2, blank=True, null=True, editable=False, default=0)
    total_no_vat     = DecimalField(_(u'Total without VAT'), max_digits=14, decimal_places=2, blank=True, null=True, editable=False, default=0)
    additional_info  = ForeignKey(AdditionalInformation, verbose_name=_(u'Additional Information'), related_name='AdditionalInformation_set', blank=True, null=True, on_delete=SET_NULL)
    payment_terms    = ForeignKey(PaymentTerms,          verbose_name=_(u'Payment Terms'),          related_name='PaymentTerms_set',          blank=True, null=True, on_delete=SET_NULL)
    payment_info     = ForeignKey(PaymentInformation, verbose_name=_(u'Payment information'), blank=True, null=True, editable=False)

    research_fields = CremeEntity.research_fields + ['name']
    excluded_fields_in_html_output = CremeEntity.excluded_fields_in_html_output + ['total_vat', 'total_no_vat', 'payment_info']

    generate_number_in_create = True #TODO: use settings instead ???

    #caches
    _productlines_cache = None
    _servicelines_cache = None

    class Meta:
        app_label = 'billing'

    def __unicode__(self):
        return self.name

    def _pre_delete(self):
        lines = list(Line.objects.filter(relations__object_entity=self.id))

        for relation in Relation.objects.filter(type__in=[REL_SUB_BILL_ISSUED, REL_SUB_BILL_RECEIVED, REL_SUB_HAS_LINE, REL_OBJ_LINE_RELATED_ITEM], subject_entity=self.id):
            relation._delete_without_transaction()

        for line in lines:
            line._delete_without_transaction()

    def invalidate_cache(self):
        self._productlines_cache = None
        self._servicelines_cache = None

    #TODO: property + cache
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

    def get_credit_notes(self):
        if self.id:
            relations = Relation.objects.filter(subject_entity=self, type=REL_OBJ_CREDIT_NOTE_APPLIED).select_related('object_entity')
            Relation.populate_real_object_entities(relations)
            return [rel.object_entity.get_real_entity() for rel in relations]
        else:
            return []

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
            #force the retrieving all lines (no slice)
            self._productlines_cache = list(ProductLine.objects.filter(relations__object_entity=self.id))
        else:
            debug('Cache HIT for product lines in document pk=%s !!' % self.id)

        return self._productlines_cache

    @property
    def service_lines(self):
        if self._servicelines_cache is None:
            self._servicelines_cache = list(ServiceLine.objects.filter(relations__object_entity=self.id))
        else:
            debug('Cache HIT for service lines in document pk=%s !!' % self.id)

        return self._servicelines_cache

    #TODO: remove (crappy api, no cache....)
    # Could replace get_x_lines()
    def get_lines(self, klass):
        return klass.objects.filter(relations__object_entity=self.id)

    def get_product_lines_total_price_exclusive_of_tax(self): #TODO: inline ???
        return round_to_2(sum(l.get_price_exclusive_of_tax() for l in self.product_lines))

    def get_product_lines_total_price_inclusive_of_tax(self):
        return round_to_2(sum(l.get_price_inclusive_of_tax() for l in self.product_lines))

    def get_service_lines_total_price_exclusive_of_tax(self):
        return round_to_2(sum(l.get_price_exclusive_of_tax() for l in self.service_lines))

    def get_service_lines_total_price_inclusive_of_tax(self):
        return round_to_2(sum(l.get_price_inclusive_of_tax() for l in self.service_lines))

    def _get_total(self):
        total_credits = sum(credit_note.total_no_vat for credit_note in self.get_credit_notes())
        total = self.get_service_lines_total_price_exclusive_of_tax() + self.get_product_lines_total_price_exclusive_of_tax() - total_credits
        return default_decimal if total < default_decimal else total

    def _get_total_with_tax(self):
        total_credits = sum(credit_note.total_vat for credit_note in self.get_credit_notes())
        total_with_tax =  self.get_service_lines_total_price_inclusive_of_tax() + self.get_product_lines_total_price_inclusive_of_tax() - total_credits
        return default_decimal if total_with_tax < default_decimal else total_with_tax

    def _pre_save_clone(self, source):
        if self.generate_number_in_create:
            self.generate_number(source.get_source())
        else:
            self.number = None

    def _copy_relations(self, source):
        #not REL_OBJ_CREDIT_NOTE_APPLIED, links to CreditNote are not cloned.
        super(Base, self)._copy_relations(source, allowed_internal=[REL_SUB_BILL_ISSUED, REL_SUB_BILL_RECEIVED])

    def _post_clone(self, source):
        source.invalidate_cache()

        for line in chain(source.product_lines, source.service_lines):
            line.clone(self)

    #TODO: Can not we really factorise with clone()
    def build(self, template):
        self._build_object(template)
        self._build_lines(template, ProductLine)
        self._build_lines(template, ServiceLine)
        self._build_relations(template)
        self._build_properties(template)
        return self

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
            line.clone(self)
        #self._post_clone(template) #TODO

    def _build_relations(self, template):
        debug("=> Clone relations")
        self._copy_relations(template)

    def _build_properties(self, template):
        debug("=> Clone properties")
        self._copy_properties(template)

    def save(self, *args, **kwargs):
        self.invalidate_cache()

        self.total_vat    = self._get_total_with_tax()
        self.total_no_vat = self._get_total()
        return super(Base, self).save(*args, **kwargs)
