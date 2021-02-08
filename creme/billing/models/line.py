# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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
from functools import partial

from django.core.exceptions import ValidationError
from django.db import models
from django.db.transaction import atomic
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme.creme_core.models import CremeEntity, Relation, Vat

from .. import constants
from ..utils import round_to_2

logger = logging.getLogger(__name__)


# TODO: use a smart workflow engine to update the BillingModel only once when
#  several lines are edited for the moment when have to re-save the model manually.

class Line(CremeEntity):
    class Discount(models.IntegerChoices):
        PERCENT     = 1, _('Percent'),
        LINE_AMOUNT = 2, _('Amount per line'),
        ITEM_AMOUNT = 3, _('Amount per unit'),

    # NB: not blank (no related item => name is filled)
    on_the_fly_item = models.CharField(_('On-the-fly line'), max_length=100, null=True)

    comment = models.TextField(_('Comment'), blank=True)

    quantity = models.DecimalField(
        _('Quantity'), max_digits=10, decimal_places=2, default=constants.DEFAULT_QUANTITY,
    )
    unit_price = models.DecimalField(
        _('Unit price'), max_digits=10, decimal_places=2, default=constants.DEFAULT_DECIMAL,
    )
    unit = models.CharField(_('Unit'), max_length=100, blank=True)

    discount = models.DecimalField(
        _('Discount'), max_digits=10, decimal_places=2, default=constants.DEFAULT_DECIMAL,
    )
    discount_unit = models.PositiveIntegerField(
        _('Discount Unit'),
        # choices=constants.DISCOUNT_UNIT.items(), default=constants.DISCOUNT_PERCENT,
        choices=Discount.choices, default=Discount.PERCENT,
    )
    vat_value = models.ForeignKey(
        Vat, verbose_name=_('VAT'), on_delete=models.PROTECT,
        # NB: these VAT should exist (see creme_core.populate), and is normally 0.0%
        default=1,
    )

    creation_label = _('Create a line')

    _related_document = False
    _related_item = None

    class Meta:
        abstract = True
        # manager_inheritance_from_future = True
        app_label = 'billing'
        verbose_name = _('Line')
        verbose_name_plural = _('Lines')
        ordering = ('created',)

    def _pre_delete(self):
        for relation in Relation.objects.filter(
            type__in=[
                constants.REL_OBJ_HAS_LINE,
                constants.REL_SUB_LINE_RELATED_ITEM,
            ],
            subject_entity=self.id,
        ):
            relation._delete_without_transaction()

    def _pre_save_clone(self, source):
        self.related_document = source._new_related_document
        self.related_item     = source.related_item

    def clean(self):
        discount_unit = self.discount_unit

        # if discount_unit == constants.DISCOUNT_PERCENT:
        if discount_unit == self.Discount.PERCENT:
            if not (0 <= self.discount <= 100):
                raise ValidationError(
                    gettext(
                        'If you choose % for your discount unit, '
                        'your discount must be between 1 and 100%'
                    ),
                    code='invalid_percentage',
                )
        # elif discount_unit == constants.DISCOUNT_LINE_AMOUNT:  # Global discount
        elif discount_unit == self.Discount.LINE_AMOUNT:  # Global discount
            if self.discount > self.unit_price * self.quantity:
                raise ValidationError(
                    gettext(
                        'Your overall discount is superior than'
                        ' the total line (unit price * quantity)'
                    ),
                    code='discount_gt_total',
                )
        else:  # DISCOUNT_ITEM_AMOUNT (Unitary discount)
            if self.discount > self.unit_price:
                raise ValidationError(
                    gettext('Your discount is superior than the unit price'),
                    code='discount_gt_unitprice',
                )

        if self.related_item:
            if self.on_the_fly_item:
                raise ValidationError(
                    gettext(
                        'You cannot set an on the fly name to a line with a related item'
                    ),
                    code='useless_name',
                )
        elif not self.on_the_fly_item:
            raise ValidationError(
                gettext('You must define a name for an on the fly item'),
                code='required_name',
            )

        super().clean()

    def clone(self, new_related_document=None):
        # BEWARE: CremeProperty and Relation are not cloned
        #         (excepted our 2 internal relations)
        self._new_related_document = new_related_document or self.related_document

        return super().clone()

    def get_absolute_url(self):
        return self.get_related_entity().get_absolute_url()

    def get_price_inclusive_of_tax(self, document=None):
        total_ht = self.get_price_exclusive_of_tax(document)
        vat_value = self.vat_value
        vat = (total_ht * vat_value.value / 100) if vat_value else 0
        return round_to_2(total_ht + vat)

    def get_raw_price(self):
        return round_to_2(self.quantity * self.unit_price)

    def get_price_exclusive_of_tax(self, document=None):
        line_discount   = self.discount
        unit_price_line = self.unit_price
        discount_unit   = self.discount_unit
        Discount = self.Discount

        # if discount_unit == constants.DISCOUNT_PERCENT:
        if discount_unit == Discount.PERCENT:
            total_after_first_discount = self.quantity * (
                unit_price_line - (unit_price_line * line_discount / 100)
            )
        # elif discount_unit == constants.DISCOUNT_LINE_AMOUNT:
        elif discount_unit == Discount.LINE_AMOUNT:
            total_after_first_discount = self.quantity * unit_price_line - line_discount
        # else:  # DISCOUNT_ITEM_AMOUNT
        else:  # ITEM_AMOUNT
            total_after_first_discount = self.quantity * (unit_price_line - line_discount)

        document     = document if document else self.related_document
        doc_discount = document.discount if document else None
        total_exclusive_of_tax = total_after_first_discount
        if doc_discount:
            total_exclusive_of_tax -= total_after_first_discount * doc_discount / 100

        return round_to_2(total_exclusive_of_tax)

    def get_related_entity(self):  # For generic views & delete
        return self.related_document

    @property
    def related_document(self):
        related = self._related_document

        if related is False:
            try:
                related = self.relations.get(
                    type=constants.REL_OBJ_HAS_LINE,
                    subject_entity=self.id,
                ).object_entity.get_real_entity()
            except Relation.DoesNotExist:
                related = None

            self._related_document = related

        return related

    @related_document.setter
    def related_document(self, billing_entity):
        assert self.pk is None, \
               'Line.related_document(setter): line is already saved (can not change any more).'
        self._related_document = billing_entity

    @property
    def related_item(self):
        if self.id and not self._related_item and not self.on_the_fly_item:
            try:
                self._related_item = self.relations.get(
                    type=constants.REL_SUB_LINE_RELATED_ITEM,
                    subject_entity=self.id,
                ).object_entity.get_real_entity()
            except Relation.DoesNotExist:
                logger.warning('Line.related_item(): relation does not exist !!')

        return self._related_item

    @related_item.setter
    def related_item(self, entity):
        assert self.pk is None, \
               'Line.related_item(setter): line is already saved (can not change any more).'
        self._related_item = entity

    @staticmethod
    def related_item_class():
        """Returns the model-class of the related item (eg: Product, Service)
        for this class of line.
        """
        raise NotImplementedError

    @atomic
    def save(self, *args, **kwargs):
        if not self.pk:  # Creation
            assert self._related_document, 'Line.related_document is required'
            assert bool(self._related_item) ^ bool(self.on_the_fly_item),\
                'Line.related_item or Line.on_the_fly_item is required'

            self.user = self._related_document.user

            super().save(*args, **kwargs)

            create_relation = partial(
                Relation.objects.create, subject_entity=self, user=self.user,
            )
            create_relation(
                type_id=constants.REL_OBJ_HAS_LINE,
                object_entity=self._related_document,
            )

            if self._related_item:
                create_relation(
                    type_id=constants.REL_SUB_LINE_RELATED_ITEM,
                    object_entity=self._related_item,
                )
        else:
            super().save(*args, **kwargs)

        # TODO: problem, if several lines are added/edited at once, lots of
        #  useless queries (workflow engine ??)
        self.related_document.save()  # Update totals
