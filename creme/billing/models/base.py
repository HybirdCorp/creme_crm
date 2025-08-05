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

from __future__ import annotations

import logging
# import warnings
# from datetime import date
from functools import partial

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.transaction import atomic
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme.creme_core.models import (
    CREME_REPLACE_NULL,
    CremeEntity,
    Currency,
    Relation,
)
from creme.creme_core.models.currency import get_default_currency_pk
from creme.creme_core.models.fields import MoneyField

from ..constants import (
    DEFAULT_DECIMAL,
    REL_OBJ_CREDIT_NOTE_APPLIED,
    REL_OBJ_HAS_LINE,
    REL_SUB_BILL_ISSUED,
    REL_SUB_BILL_RECEIVED,
    REL_SUB_HAS_LINE,
)
from . import other_models
from .fields import BillingDiscountField
from .line import Line

logger = logging.getLogger(__name__)


class Base(CremeEntity):
    name = models.CharField(_('Name'), max_length=100)
    number = models.CharField(_('Number'), max_length=100, blank=True).set_tags(clonable=False)

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
        null=True, editable=False,
        related_name='+', on_delete=models.SET_NULL,
    ).set_tags(enumerable=False)
    shipping_address = models.ForeignKey(
        settings.PERSONS_ADDRESS_MODEL, verbose_name=_('Shipping address'),
        null=True, editable=False,
        related_name='+', on_delete=models.SET_NULL,
    ).set_tags(enumerable=False)

    currency = models.ForeignKey(
        Currency, verbose_name=_('Currency'), related_name='+',
        default=get_default_currency_pk,
        on_delete=models.PROTECT,
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

    # NB: REL_SUB_HAS_LINE is excluded because we must retrieve the line to delete them
    # TODO: signal to delete a line when the corresponding Relation is deleted?
    _DELETABLE_INTERNAL_RTYPE_IDS = (
        REL_SUB_BILL_ISSUED,
        REL_SUB_BILL_RECEIVED,
        # REL_SUB_HAS_LINE,
    )

    creation_label = _('Create an accounting document')

    # Is the "number" fields automatically filled at creation if a number
    # generation configuration is available (i.e. registered model + managed
    # emitter Organisation).
    # Notice that if the configuration allows the manual edition (i.e.
    # NumberGeneratorItem.is_edition_allowed == True) & a number is given by the
    # NumberGeneratorItem.is_edition_allowed == True) & a number is given by the
    # user, no automatic number overrides the user's value.
    # NB: number is set in billing.signals.generate_number()
    generate_number_in_create = True

    # Caches
    _source = None
    _source_rel = None
    _target = None
    _target_rel = None
    _creditnotes_cache = None

    class Meta:
        abstract = True
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

        # TODO: see remark to _DELETABLE_INTERNAL_RTYPE_IDS
        for relation in Relation.objects.filter(
            type=REL_SUB_HAS_LINE, subject_entity=self.id
        ):
            # NB: see billing.signals.manage_line_deletion().
            #     We avoid to compute the total at each deletion because the
            #     instance is totally deleted, so its slow & useless.
            relation._avoid_billing_total_update = True
            relation._delete_without_transaction()

        for line in lines:
            line.delete()

    def clean(self):
        self._clean_source_n_target()
        super().clean()

    def invalidate_cache(self):
        self._lines_cache.clear()
        self._creditnotes_cache = None

    @property
    def source(self):
        if not self._source:
            self._source_rel = rel = self.get_relations(REL_SUB_BILL_ISSUED)[0]
            self._source = rel.real_object

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
            self._target_rel = rel = self.get_relations(REL_SUB_BILL_RECEIVED)[0]
            self._target = rel.real_object

        return self._target

    @target.setter
    def target(self, person):
        if self.pk:  # Edition:
            old_target = self.target
            if old_target != person:
                self._target = person
        else:
            self._target = person

    # TODO: property ?
    def get_credit_notes(self):
        credit_notes = self._creditnotes_cache

        if credit_notes is None:
            self._creditnotes_cache = credit_notes = []

            if self.id:
                credit_notes.extend(
                    rel.real_object
                    for rel in Relation.objects
                                       .filter(
                                           subject_entity=self.id,
                                           type=REL_OBJ_CREDIT_NOTE_APPLIED,
                                       ).prefetch_related('real_object')
                    if not rel.real_object.is_deleted
                )

        return credit_notes

    def get_lines(self, klass):
        assert issubclass(klass, Line)
        assert not klass._meta.abstract, \
            '"klass" cannot be an abstract model (use ProductLine or ServiceLine)'

        cache = self._lines_cache
        lines = cache.get(klass)

        if lines is None:
            lines = cache[klass] = klass.objects.filter(
                relations__object_entity=self.id,
                relations__type=REL_OBJ_HAS_LINE,
            ).order_by('order')

        return lines

    def iter_all_lines(self):
        from ..core.line import line_registry  # TODO: in class attribute ?

        for line_cls in line_registry:
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

    # def _pre_save_clone(self, source):
    #     warnings.warn(
    #         'The method Base._pre_save_clone() is deprecated.',
    #         DeprecationWarning,
    #     )
    #
    #     self.source = source.source
    #     self.target = source.target
    #
    #     self.number = ''
    #
    #     self._address_auto_copy = False
    #
    # def _post_clone(self, source):
    #     warnings.warn(
    #         'The method Base._post_clone() is deprecated.',
    #         DeprecationWarning,
    #     )
    #
    #     source.invalidate_cache()
    #
    #     for line in source.iter_all_lines():
    #         line.clone(self)
    #
    # def _post_save_clone(self, source):
    #     warnings.warn(
    #         'The method Base._post_save_clone() is deprecated.',
    #         DeprecationWarning,
    #     )
    #
    #     save = False
    #
    #     if source.billing_address is not None:
    #         self.billing_address = source.billing_address.clone(self)
    #         save = True
    #
    #     if source.shipping_address is not None:
    #         self.shipping_address = source.shipping_address.clone(self)
    #         save = True
    #
    #     if save:
    #         self.save()

    # def build(self, template: Base):
    #     warnings.warn(
    #         'The method billing.models.Base.build() is deprecated; '
    #         'use the new conversion/spawning systems instead.',
    #         DeprecationWarning,
    #     )
    #     self._address_auto_copy = False
    #
    #     self._build_object(template)
    #     self._post_save_clone(template)  # Copy addresses
    #     self._post_clone(template)  # Copy lines
    #     self._build_relations(template)
    #     self._build_properties(template)
    #
    #     return self
    #
    # build.alters_data = True
    #
    # def _build_object(self, template: Base):
    #     warnings.warn(
    #         'The method billing.models.Base._build_object() is deprecated.',
    #         DeprecationWarning,
    #     )
    #
    #     self.user         = template.user
    #     self.name         = template.name
    #     self.number       = template.number
    #     self.discount     = template.discount
    #     self.currency     = template.currency
    #     self.comment      = template.comment
    #     self.payment_info = template.payment_info
    #
    #     self.issuing_date = self.expiration_date = date.today()
    #
    #     self.source = template.source
    #     self.target = template.target
    #
    #     self.save()
    #
    #     # NB: not copied:
    #     # - additional_info
    #     # - payment_terms
    #
    # def _build_relations(self, template: Base):
    #     warnings.warn(
    #         'The method billing.models.Base._build_relations() is deprecated.',
    #         DeprecationWarning,
    #     )
    #     self._copy_relations(template)
    #
    # def _build_properties(self, template: Base):
    #     warnings.warn(
    #         'The method billing.models.Base._build_properties() is deprecated.',
    #         DeprecationWarning,
    #     )
    #     self._copy_properties(template)

    # TODO: remove *args, **kwargs
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

    def _update_addresses(self):
        # TODO: recycle instance instead?
        self.billing_address.delete()
        self.shipping_address.delete()

        self._create_addresses()

    def _set_basic_payment_info(self):
        source = self._source

        if source:
            payment_info = self.payment_info
            pinfo_orga_id = payment_info.organisation_id if payment_info else None

            if source.id != pinfo_orga_id:
                self.payment_info = None

            if self.payment_info is None:  # Optimization
                self.payment_info = other_models.PaymentInformation.objects.filter(
                    organisation=source.id,
                ).order_by('-is_default').first()

    def _update_totals(self):
        "Hint: facilitate the modification by extending/external apps."
        self.total_vat = self._get_total_with_tax()
        self.total_no_vat = self._get_total()

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

            # Its seems it's not useful to extend update_fields because Line.save(),
            # which garanties the totals are updated, does not use <update_fields> :
            #    if update_fields is not None:
            #        update_fields = { 'total_vat', 'total_no_vat', *update_fields}
            self._update_totals()

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
                self._update_addresses()
