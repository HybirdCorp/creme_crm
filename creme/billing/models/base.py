# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2022  Hybird
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

import logging
# import warnings
from datetime import date
from functools import partial

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.transaction import atomic
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme.creme_core.constants import DEFAULT_CURRENCY_PK
from creme.creme_core.models import (
    CREME_REPLACE_NULL,
    CremeEntity,
    Currency,
    Relation,
)
from creme.creme_core.models.fields import MoneyField

from ..constants import (
    DEFAULT_DECIMAL,
    REL_OBJ_CREDIT_NOTE_APPLIED,
    REL_OBJ_HAS_LINE,
    REL_OBJ_LINE_RELATED_ITEM,
    REL_SUB_BILL_ISSUED,
    REL_SUB_BILL_RECEIVED,
    REL_SUB_HAS_LINE,
)
from . import other_models
from .algo import ConfigBillingAlgo
from .fields import BillingDiscountField

logger = logging.getLogger(__name__)


class Base(CremeEntity):
    name = models.CharField(_('Name'), max_length=100)
    number = models.CharField(_('Number'), max_length=100, blank=True)

    issuing_date = models.DateField(
        _('Issuing date'), blank=True, null=True,
    ).set_tags(optional=True)
    expiration_date = models.DateField(
        _('Expiration date'), blank=True, null=True,
    ).set_tags(optional=True)

    discount = BillingDiscountField(
        _('Overall discount'),
        default=DEFAULT_DECIMAL, max_digits=10, decimal_places=2,
    )

    billing_address = models.ForeignKey(
        settings.PERSONS_ADDRESS_MODEL, verbose_name=_('Billing address'),
        null=True, editable=False,  # blank=True
        related_name='+', on_delete=models.SET_NULL,
    ).set_tags(enumerable=False)
    shipping_address = models.ForeignKey(
        settings.PERSONS_ADDRESS_MODEL, verbose_name=_('Shipping address'),
        null=True, editable=False,  # blank=True
        related_name='+', on_delete=models.SET_NULL,
    ).set_tags(enumerable=False)

    currency = models.ForeignKey(
        Currency, verbose_name=_('Currency'), related_name='+',
        default=DEFAULT_CURRENCY_PK, on_delete=models.PROTECT,
    )

    comment = models.TextField(_('Comment'), blank=True).set_tags(optional=True)

    total_vat = MoneyField(
        _('Total with VAT'), default=0,
        max_digits=14, decimal_places=2,
        blank=True, null=True, editable=False,
    )
    total_no_vat = MoneyField(
        _('Total without VAT'), default=0,
        max_digits=14, decimal_places=2,
        blank=True, null=True, editable=False,
    )

    additional_info = models.ForeignKey(
        other_models.AdditionalInformation,
        verbose_name=_('Additional Information'),
        related_name='+',
        blank=True, null=True, on_delete=CREME_REPLACE_NULL,
    ).set_tags(clonable=False, optional=True)
    payment_terms = models.ForeignKey(
        other_models.PaymentTerms,
        verbose_name=_('Payment Terms'),
        related_name='+',
        blank=True, null=True, on_delete=CREME_REPLACE_NULL,
    ).set_tags(clonable=False, optional=True)
    payment_info = models.ForeignKey(
        other_models.PaymentInformation,
        verbose_name=_('Payment information'),
        null=True, on_delete=models.SET_NULL,
        blank=True, editable=False,
    ).set_tags(optional=True)
    payment_type = models.ForeignKey(
        other_models.SettlementTerms,
        verbose_name=_('Settlement terms'),
        blank=True, null=True, on_delete=CREME_REPLACE_NULL,
    ).set_tags(optional=True)

    creation_label = _('Create an accounting document')

    generate_number_in_create = True  # TODO: use settings/SettingValue instead ???

    # Caches
    _source = None
    _source_rel = None
    _target = None
    _target_rel = None
    _creditnotes_cache = None

    class Meta:
        abstract = True
        # manager_inheritance_from_future = True
        app_label = 'billing'
        ordering = ('name',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._lines_cache = {}  # Key: Line class ; Value: Lines instances (list)
        self._address_auto_copy = True

    def __str__(self):
        return self.name

    def _clean_source_n_target(self):
        if not self.pk:  # Creation
            if not self._source:
                raise ValidationError(gettext('Source organisation is required.'))

            if not self._target:
                raise ValidationError(gettext('Target is required.'))

    def _pre_delete(self):
        lines = [*self.iter_all_lines()]

        for relation in Relation.objects.filter(
                type__in=[
                    REL_SUB_BILL_ISSUED,
                    REL_SUB_BILL_RECEIVED,
                    REL_SUB_HAS_LINE,
                    REL_OBJ_LINE_RELATED_ITEM,
                ],
                subject_entity=self.id):
            relation._delete_without_transaction()

        for line in lines:
            line._delete_without_transaction()

    def clean(self):
        self._clean_source_n_target()
        super().clean()

    def invalidate_cache(self):
        self._lines_cache.clear()
        self._creditnotes_cache = None

    @property
    def source(self):
        if not self._source:
            self._source_rel = rel = self.relations.get(type=REL_SUB_BILL_ISSUED)
            self._source = rel.object_entity.get_real_entity()

        return self._source

    @source.setter
    def source(self, organisation):
        if self.pk:  # Edition:
            old_source = self.source
            if old_source != organisation:
                self._source = organisation
        else:
            self._source = organisation

    # TODO: factorise
    @property
    def target(self):
        if not self._target:
            self._target_rel = rel = self.relations.get(type=REL_SUB_BILL_RECEIVED)
            self._target = rel.object_entity.get_real_entity()

        return self._target

    @target.setter
    def target(self, person):
        if self.pk:  # Edition:
            old_target = self.target
            if old_target != person:
                self._target = person
        else:
            self._target = person

    # def get_source(self):
    #     warnings.warn(
    #         'billing.Base.get_source() is deprecated ; '
    #         'use the property "source" instead.',
    #         DeprecationWarning,
    #     )
    #
    #     try:
    #         return Relation.objects.get(
    #             subject_entity=self.id,
    #             type=REL_SUB_BILL_ISSUED,
    #         ).object_entity if self.id else None
    #     except Relation.DoesNotExist:
    #         return None

    # def get_target(self):
    #     warnings.warn(
    #         'billing.Base.get_target() is deprecated ; '
    #         'use the property "target" instead.',
    #         DeprecationWarning,
    #     )
    #
    #     try:
    #         return Relation.objects.get(
    #             subject_entity=self.id,
    #             type=REL_SUB_BILL_RECEIVED,
    #         ).object_entity if self.id else None
    #     except Relation.DoesNotExist:
    #         return None

    # TODO: property ?
    def get_credit_notes(self):
        credit_notes = self._creditnotes_cache

        if credit_notes is None:
            self._creditnotes_cache = credit_notes = []

            if self.id:
                relations = Relation.objects.filter(
                    subject_entity=self.id,
                    type=REL_OBJ_CREDIT_NOTE_APPLIED,
                ).select_related('object_entity')
                Relation.populate_real_object_entities(relations)
                credit_notes.extend(
                    rel.object_entity.get_real_entity()
                    for rel in relations
                    if not rel.object_entity.is_deleted
                )

        return credit_notes

    # TODO: remove "source" argument?
    def generate_number(self, source=None):
        # Lazy loading of number generators
        from creme.billing.registry import algo_registry

        if source is None:
            source = self.source

        if not self.number:
            self.number = '0'

        if source:
            real_content_type = self.entity_type

            try:
                name_algo = ConfigBillingAlgo.objects.get(
                    organisation=source, ct=real_content_type,
                ).name_algo
                algo = algo_registry.get_algo(name_algo)
                self.number = algo().generate_number(source, real_content_type)
            except Exception as e:
                logger.info('billing.generate_number(): number cannot be generated (%s)', e)

    def get_lines(self, klass):
        assert not klass._meta.abstract, \
            '"klass" cannot be an abstract model (use ProductLine or ServiceLine)'

        cache = self._lines_cache
        lines = cache.get(klass)

        if lines is None:
            lines = cache[klass] = klass.objects.filter(
                relations__object_entity=self.id,
                relations__type=REL_OBJ_HAS_LINE,
            )

        return lines

    def iter_all_lines(self):
        from ..registry import lines_registry  # TODO: in class attribute ?

        for line_cls in lines_registry:
            yield from self.get_lines(line_cls)

    def _get_lines_total_n_creditnotes_total(self):
        creditnotes_total = sum(
            credit_note.total_no_vat for credit_note in self.get_credit_notes()
        )
        lines_total = sum(
            line.get_price_exclusive_of_tax(self) for line in self.iter_all_lines()
        )

        return lines_total, creditnotes_total

    def _get_lines_total_n_creditnotes_total_with_tax(self):
        creditnotes_total = sum(
            credit_note.total_vat for credit_note in self.get_credit_notes()
        )
        lines_total_with_tax = sum(
            line.get_price_inclusive_of_tax(self) for line in self.iter_all_lines()
        )

        return lines_total_with_tax, creditnotes_total

    def _get_total(self):
        lines_total, creditnotes_total = self._get_lines_total_n_creditnotes_total()

        return max(DEFAULT_DECIMAL, lines_total - creditnotes_total)

    def _get_total_with_tax(self):
        lines_total_with_tax, creditnotes_total = \
            self._get_lines_total_n_creditnotes_total_with_tax()

        return max(DEFAULT_DECIMAL, lines_total_with_tax - creditnotes_total)

    def _pre_save_clone(self, source):
        self.source = source.source
        self.target = source.target

        # if self.generate_number_in_create:
        #     self.generate_number(source.source)
        # else:
        #     self.number = ''
        self.number = ''

        self._address_auto_copy = False

    def _copy_relations(self, source):
        from ..registry import relationtype_converter

        # Not REL_OBJ_CREDIT_NOTE_APPLIED, links to CreditNote are not cloned.
        relation_create = Relation.objects.create
        class_map = relationtype_converter.get_class_map(source, self)
        super()._copy_relations(
            source,
            # allowed_internal=[REL_SUB_BILL_ISSUED, REL_SUB_BILL_RECEIVED],
        )

        for relation in source.relations.filter(
                type__is_internal=False,
                type__is_copiable=True,
                type__in=class_map.keys()):
            relation_create(
                user_id=relation.user_id,
                subject_entity=self,
                type=class_map[relation.type],
                object_entity_id=relation.object_entity_id,
            )

    def _post_clone(self, source):
        source.invalidate_cache()

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
        self._address_auto_copy = False

        self._build_object(template)
        self._post_save_clone(template)  # Copy addresses
        self._post_clone(template)  # Copy lines
        self._build_relations(template)
        self._build_properties(template)

        return self

    def _build_object(self, template):
        logger.debug('=> Clone base object')

        self.user         = template.user
        self.name         = template.name
        self.number       = template.number
        self.discount     = template.discount
        self.currency     = template.currency
        self.comment      = template.comment
        self.payment_info = template.payment_info

        self.issuing_date = self.expiration_date = date.today()

        self.source = template.source
        self.target = template.target

        self.save()

        # NB: not copied:
        # - additional_info
        # - payment_terms

    def _build_relations(self, template):
        logger.debug('=> Clone relations')
        self._copy_relations(template)

    def _build_properties(self, template):
        logger.debug('=> Clone properties')
        self._copy_properties(template)

    def _create_addresses(self, *args, **kwargs):
        from ..utils import copy_or_create_address

        target = self._target
        self.billing_address = copy_or_create_address(
            target.billing_address, owner=self, name=_('Billing address'),
        )
        self.shipping_address = copy_or_create_address(
            target.shipping_address, owner=self, name=_('Shipping address'),
        )

        super().save(
            *args,
            **{
                **kwargs,
                'update_fields': ('billing_address', 'shipping_address'),
            }
        )

    def _set_basic_payment_info(self):
        source = self._source

        if source:
            payment_info = self.payment_info
            pinfo_orga_id = payment_info.organisation_id if payment_info else None

            if source.id != pinfo_orga_id:
                self.payment_info = None

            if self.payment_info is None:  # Optimization
                # source_pis = other_models.PaymentInformation.objects.filter(
                #     organisation=source.id,
                # )[:2]
                # if len(source_pis) == 1:
                #     self.payment_info = source_pis[0]
                self.payment_info = other_models.PaymentInformation.objects.filter(
                    organisation=source.id,
                ).order_by('-is_default').first()

    @atomic
    def save(self, *args, **kwargs):
        create_relation = partial(
            Relation.objects.create, subject_entity=self, user=self.user,
        )
        source = self._source
        target = self._target

        self._set_basic_payment_info()

        if not self.pk:  # Creation
            self._clean_source_n_target()

            if self.generate_number_in_create:
                self.generate_number(source)

            super().save(*args, **kwargs)

            self._source_rel = create_relation(
                type_id=REL_SUB_BILL_ISSUED,   object_entity=source,
            )
            self._target_rel = create_relation(
                type_id=REL_SUB_BILL_RECEIVED, object_entity=target,
            )

            if self._address_auto_copy:
                self._create_addresses()
        else:  # Edition
            self.invalidate_cache()

            self.total_vat    = self._get_total_with_tax()
            self.total_no_vat = self._get_total()

            super().save(*args, **kwargs)

            old_source_rel = self._source_rel
            if old_source_rel and old_source_rel.object_entity_id != source.id:
                old_source_rel.delete()
                self._source_rel = create_relation(
                    type_id=REL_SUB_BILL_ISSUED, object_entity=source,
                )

            # TODO: factorise
            old_target_rel = self._target_rel
            if old_target_rel and old_target_rel.object_entity_id != target.id:
                old_target_rel.delete()
                self._target_rel = create_relation(
                    type_id=REL_SUB_BILL_RECEIVED, object_entity=target,
                )
