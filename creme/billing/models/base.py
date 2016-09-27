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

from datetime import date
from itertools import chain
import logging
import warnings

from django.conf import settings
from django.db.models import (CharField, TextField, ForeignKey, DateField,
        SET_NULL, PROTECT)
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.constants import DEFAULT_CURRENCY_PK
from creme.creme_core.models import CremeEntity, Relation, Currency
from creme.creme_core.models.fields import MoneyField

from ..constants import (REL_SUB_BILL_ISSUED, REL_SUB_BILL_RECEIVED,
        REL_SUB_HAS_LINE, REL_OBJ_HAS_LINE, REL_OBJ_LINE_RELATED_ITEM,
        REL_OBJ_CREDIT_NOTE_APPLIED, DEFAULT_DECIMAL)
from ..utils import round_to_2

from .algo import ConfigBillingAlgo
from .fields import BillingDiscountField
from .other_models import AdditionalInformation, PaymentTerms, PaymentInformation
from .product_line import ProductLine
from .service_line import ServiceLine


logger = logging.getLogger(__name__)


class Base(CremeEntity):
    name             = CharField(_(u'Name'), max_length=100)
    number           = CharField(_(u'Number'), max_length=100, blank=True)
    issuing_date     = DateField(_(u"Issuing date"), blank=True, null=True)\
                                .set_tags(optional=True)
    expiration_date  = DateField(_(u"Expiration date"), blank=True, null=True)\
                                .set_tags(optional=True)
    discount         = BillingDiscountField(_(u'Overall discount'), default=DEFAULT_DECIMAL,
                                            max_digits=10, decimal_places=2,
                                           )
    billing_address  = ForeignKey(settings.PERSONS_ADDRESS_MODEL,
                                  verbose_name=_(u'Billing address'),
                                  related_name='+',
                                  blank=True, null=True, editable=False, on_delete=SET_NULL,
                                 ).set_tags(enumerable=False)
    shipping_address = ForeignKey(settings.PERSONS_ADDRESS_MODEL,
                                  verbose_name=_(u'Shipping address'),
                                  related_name='+',
                                  blank=True, null=True, editable=False, on_delete=SET_NULL,
                                 ).set_tags(enumerable=False)
    currency         = ForeignKey(Currency, verbose_name=_(u'Currency'),
                                  related_name='+',
                                  default=DEFAULT_CURRENCY_PK, on_delete=PROTECT,
                                 )
    comment          = TextField(_(u'Comment'), blank=True).set_tags(optional=True)
    total_vat        = MoneyField(_(u'Total with VAT'), default=0,
                                  max_digits=14, decimal_places=2,
                                  blank=True, null=True, editable=False,
                                 )
    total_no_vat     = MoneyField(_(u'Total without VAT'), default=0,
                                  max_digits=14, decimal_places=2,
                                  blank=True, null=True, editable=False,
                                 )
    additional_info  = ForeignKey(AdditionalInformation,
                                  verbose_name=_(u'Additional Information'),
                                  related_name='+',
                                  blank=True, null=True, on_delete=SET_NULL,
                                 ).set_tags(clonable=False, optional=True)
    payment_terms    = ForeignKey(PaymentTerms, verbose_name=_(u'Payment Terms'),
                                  related_name='+',
                                  blank=True, null=True, on_delete=SET_NULL,
                                 ).set_tags(clonable=False, optional=True)
    payment_info     = ForeignKey(PaymentInformation, verbose_name=_(u'Payment information'),
                                  blank=True, null=True, editable=False, on_delete=SET_NULL,
                                 ).set_tags(optional=True)

    creation_label = _('Add an accounting document')

    generate_number_in_create = True # TODO: use settings instead ???

    # Caches
    # _productlines_cache = None
    # _servicelines_cache = None
    _creditnotes_cache = None

    class Meta:
        abstract = True
        app_label = 'billing'
        ordering = ('name',)

    def __init__(self, *args, **kwargs):
        super(Base, self).__init__(*args, **kwargs)
        self._lines_cache = {}  # Key: Line class ; Value: Lines instances (list)

    def __unicode__(self):
        return self.name

    def _pre_delete(self):
        # lines = list(chain(self.product_lines, self.service_lines))
        lines = list(self.iter_all_lines())

        for relation in Relation.objects.filter(type__in=[REL_SUB_BILL_ISSUED,
                                                          REL_SUB_BILL_RECEIVED,
                                                          REL_SUB_HAS_LINE,
                                                          REL_OBJ_LINE_RELATED_ITEM,
                                                         ],
                                                subject_entity=self.id):
            relation._delete_without_transaction()

        for line in lines:
            line._delete_without_transaction()

    def invalidate_cache(self):
        self._lines_cache.clear()
        # self._productlines_cache = None
        # self._servicelines_cache = None
        self._creditnotes_cache = None

    # TODO: property + cache
    # TODO: factorise with get_target()
    # TODO: return an Organisation instead of a CremeEntity ?? <- If doing this check calls to .get_source().get_real_entity()
    def get_source(self):
        try:
            return Relation.objects.get(subject_entity=self.id, type=REL_SUB_BILL_ISSUED).object_entity if self.id else None
        except Relation.DoesNotExist:
            return None

    def get_target(self):
        try:
            return Relation.objects.get(subject_entity=self.id, type=REL_SUB_BILL_RECEIVED).object_entity if self.id else None
        except Relation.DoesNotExist:
            return None

    def get_credit_notes(self):
        credit_notes = self._creditnotes_cache

        if credit_notes is None:
            self._creditnotes_cache = credit_notes = []

            if self.id:
                relations = Relation.objects.filter(subject_entity=self.id,
                                                    type=REL_OBJ_CREDIT_NOTE_APPLIED,
                                                   ) \
                                            .select_related('object_entity')
                Relation.populate_real_object_entities(relations)
                credit_notes.extend(rel.object_entity.get_real_entity()
                                        for rel in relations
                                            if not rel.object_entity.is_deleted
                                   )

        return credit_notes

    def generate_number(self, source=None):
        from creme.billing.registry import algo_registry  # Lazy loading of number generators

        if source is None:
            source = self.get_source()
        self.number = 0

        if source:
            real_content_type = self.entity_type

            try:
                name_algo = ConfigBillingAlgo.objects.get(organisation=source, ct=real_content_type).name_algo
                algo = algo_registry.get_algo(name_algo)
                self.number = algo().generate_number(source, real_content_type)
            except Exception as e:
                logger.debug('Exception during billing.generate_number(): %s', e)

    @property
    def product_lines(self):
        warnings.warn("billing.Base.product_lines() method is deprecated; use get_lines() instead",
                      DeprecationWarning
                     )

        # if self._productlines_cache is None:
        #     queryset = ProductLine.objects.filter(relations__object_entity=self.id)
        #     bool(queryset)  # Force the retrieving all lines (no slice)
        #     self._productlines_cache = queryset
        # else:
        #     logger.debug('Cache HIT for product lines in document pk=%s !!' % self.id)
        #
        # return self._productlines_cache
        return self.get_lines(ProductLine)

    @property
    def service_lines(self):
        warnings.warn("billing.Base.product_lines() method is deprecated; use get_lines() instead",
                      DeprecationWarning
                     )

        # if self._servicelines_cache is None:
        #     queryset = ServiceLine.objects.filter(relations__object_entity=self.id)
        #     bool(queryset)
        #     self._servicelines_cache = queryset
        # else:
        #     logger.debug('Cache HIT for service lines in document pk=%s !!' % self.id)
        #
        # return self._servicelines_cache
        return self.get_lines(ServiceLine)

    def get_lines(self, klass):
        assert not klass._meta.abstract, '"klass" cannot be an abstract model (use ProductLine or ServiceLine)'

        cache = self._lines_cache
        lines = cache.get(klass)

        if lines is None:
            lines = cache[klass] = klass.objects.filter(relations__object_entity=self.id,
                                                        relations__type=REL_OBJ_HAS_LINE,
                                                       )

        return lines

    # TODO: round_to_2 is already used when processing per lines prices.
    # Summing already rounded values has no effect, so the next 4 calls to round_to_2
    # could be deleted.
    def get_product_lines_total_price_exclusive_of_tax(self):
        warnings.warn("billing.Base.get_product_lines_total_price_exclusive_of_tax() method is deprecated.",
                      DeprecationWarning
                     )
        return round_to_2(sum(l.get_price_exclusive_of_tax(self) for l in self.product_lines))

    def get_product_lines_total_price_inclusive_of_tax(self):
        warnings.warn("billing.Base.get_product_lines_total_price_inclusive_of_tax() method is deprecated.",
                      DeprecationWarning
                     )
        return round_to_2(sum(l.get_price_inclusive_of_tax(self) for l in self.product_lines))

    def get_service_lines_total_price_exclusive_of_tax(self):
        warnings.warn("billing.Base.get_service_lines_total_price_exclusive_of_tax() method is deprecated.",
                      DeprecationWarning
                     )
        return round_to_2(sum(l.get_price_exclusive_of_tax(self) for l in self.service_lines))

    def get_service_lines_total_price_inclusive_of_tax(self):
        warnings.warn("billing.Base.get_service_lines_total_price_inclusive_of_tax() method is deprecated.",
                      DeprecationWarning
                     )
        return round_to_2(sum(l.get_price_inclusive_of_tax(self) for l in self.service_lines))

    def iter_all_lines(self):
        from ..registry import lines_registry

        for line_cls in lines_registry:
            for line in chain(self.get_lines(line_cls)):
                yield line

    def _get_lines_total_n_creditnotes_total(self):
        creditnotes_total = sum(credit_note.total_no_vat
                                    for credit_note in self.get_credit_notes()
                               )
        # lines_total = self.get_service_lines_total_price_exclusive_of_tax() \
        #             + self.get_product_lines_total_price_exclusive_of_tax()
        lines_total = sum(l.get_price_exclusive_of_tax(self) for l in self.iter_all_lines())

        return lines_total, creditnotes_total

    def _get_lines_total_n_creditnotes_total_with_tax(self):
        creditnotes_total = sum(credit_note.total_vat for credit_note in self.get_credit_notes())
        # lines_total_with_tax = self.get_service_lines_total_price_inclusive_of_tax() \
        #                      + self.get_product_lines_total_price_inclusive_of_tax()
        lines_total_with_tax = sum(l.get_price_inclusive_of_tax(self) for l in self.iter_all_lines())

        return lines_total_with_tax, creditnotes_total

    def _get_total(self):
        lines_total, creditnotes_total = self._get_lines_total_n_creditnotes_total()

        return max(DEFAULT_DECIMAL, lines_total - creditnotes_total)

    def _get_total_with_tax(self):
        lines_total_with_tax, creditnotes_total = self._get_lines_total_n_creditnotes_total_with_tax()

        return max(DEFAULT_DECIMAL, lines_total_with_tax - creditnotes_total)

    def _pre_save_clone(self, source):
        if self.generate_number_in_create:
            self.generate_number(source.get_source())
        else:
            # self.number = None
            self.number = ''

    def _copy_relations(self, source):
        from ..registry import relationtype_converter
        # Not REL_OBJ_CREDIT_NOTE_APPLIED, links to CreditNote are not cloned.
        relation_create = Relation.objects.create
        class_map = relationtype_converter.get_class_map(source, self)
        super(Base, self)._copy_relations(source, allowed_internal=[REL_SUB_BILL_ISSUED, REL_SUB_BILL_RECEIVED])

        for relation in source.relations.filter(type__is_internal=False,
                                                type__is_copiable=True,
                                                type__in=class_map.keys()):
            relation_create(user_id=relation.user_id,
                            subject_entity=self,
                            type=class_map[relation.type],
                            object_entity_id=relation.object_entity_id,
                           )

    def _post_clone(self, source):
        source.invalidate_cache()

        # for line in chain(source.product_lines, source.service_lines):
        for line in source.iter_all_lines():
            line.clone(self)

    # TODO: factorise with persons ??
    def _post_save_clone(self, source):
        save = False

        if source.billing_address is not None:
            self.billing_address = source.billing_address.clone(self)
            save = True

        if source.shipping_address is not None:
            self.shipping_address = source.shipping_address.clone(self)
            save = True

        if save:
            self.save()

    # TODO: Can not we really factorise with clone()
    def build(self, template):
        self._build_object(template)
        self._post_save_clone(template)  # Copy addresses
        # self._build_lines(template, ProductLine)
        # self._build_lines(template, ServiceLine)
        self._post_clone(template)  # Copy lines
        self._build_relations(template)
        self._build_properties(template)
        return self

    def _build_object(self, template):
        logger.debug("=> Clone base object")
        today                   = date.today()
        self.user               = template.user
        self.name               = template.name
        self.number             = template.number
        self.issuing_date       = today
        self.expiration_date    = today
        self.discount           = template.discount
        self.currency           = template.currency
        self.comment            = template.comment
        self.payment_info       = template.payment_info
        self.save()

        # NB: not copied:
        # - additional_info
        # - payment_terms

    def _build_lines(self, template, klass):
        # logger.debug("=> Clone lines")
        warnings.warn("billing.Base._build_lines() method is deprecated; use _post_clone() instead",
                      DeprecationWarning
                     )
        for line in template.get_lines(klass):
            line.clone(self)

    def _build_relations(self, template):
        logger.debug("=> Clone relations")
        self._copy_relations(template)

    def _build_properties(self, template):
        logger.debug("=> Clone properties")
        self._copy_properties(template)

    def save(self, *args, **kwargs):
        if self.pk:
            self.invalidate_cache()

            self.total_vat    = self._get_total_with_tax()
            self.total_no_vat = self._get_total()

        return super(Base, self).save(*args, **kwargs)
