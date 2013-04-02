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

from functools import partial
from decimal import Decimal
from logging import warn #debug

from django.core.exceptions import ValidationError
from django.db.models import (CharField, IntegerField, DecimalField, BooleanField,
                              TextField, PositiveIntegerField, ForeignKey, PROTECT)
from django.db.models.query_utils import Q
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils.translation import ugettext_lazy as _, ugettext

from creme.creme_core.models import CremeEntity, Relation
from creme.creme_core.core.function_field import FunctionField

from creme.billing.constants import REL_OBJ_HAS_LINE, REL_SUB_LINE_RELATED_ITEM, PERCENT_PK, DISCOUNT_UNIT
from creme.billing.models.other_models import Vat
from creme.billing.utils import round_to_2


default_decimal = Decimal()
default_quantity = Decimal('1.00')

PRODUCT_LINE_TYPE = 1
SERVICE_LINE_TYPE = 2

LINE_TYPES = {
    PRODUCT_LINE_TYPE: _(u"Product"),
    SERVICE_LINE_TYPE: _(u"Service"),
}

class _LineTypeField(FunctionField):
    name         = "get_verbose_type"
    verbose_name = _(u'Line type')
    has_filter   = True
    choices      = LINE_TYPES.items()

    @classmethod
    def filter_in_result(cls, search_string):
        return Q(type=search_string)


#TODO: use a smart workflow engine to update the BillingModel only once when several lines are edited
#      for the moment when have to re-save the model manually.

class Line(CremeEntity):
    on_the_fly_item = CharField(_(u'On-the-fly line'), max_length=100, blank=True, null=True)
    comment         = TextField(_('Comment'), blank=True, null=True)
    quantity        = DecimalField(_(u'Quantity'), max_digits=10, decimal_places=2, default=default_quantity)
    unit_price      = DecimalField(_(u'Unit price'), max_digits=10, decimal_places=2, default=default_decimal)
    unit            = CharField(_(u'Unit'), max_length=100, blank=True, null=True)
    discount        = DecimalField(_(u'Discount'), max_digits=10, decimal_places=2, default=default_decimal)
    discount_unit   = PositiveIntegerField(_(u'Discount Unit'), blank=True, null=True, choices=DISCOUNT_UNIT.items(), default=PERCENT_PK)
    total_discount  = BooleanField(_('Total discount ?'))
    vat_value       = ForeignKey(Vat, verbose_name=_(u'VAT'), blank=True, null=True, on_delete=PROTECT) #TODO null=False
    type            = IntegerField(_(u'Type'), blank=False, null=False, choices=LINE_TYPES.items(), editable=False).set_tags(viewable=False)

    #excluded_fields_in_html_output = CremeEntity.excluded_fields_in_html_output + ['type']
    #header_filter_exclude_fields   = CremeEntity.header_filter_exclude_fields + ['type']
    function_fields = CremeEntity.function_fields.new(_LineTypeField())
    creation_label = _('Add a line')

    _related_document = None
    _related_item = None

    class Meta:
        app_label = 'billing'
        verbose_name = _(u'Line')
        verbose_name_plural = _(u'Lines')

    def _pre_delete(self):
        for relation in Relation.objects.filter(type__in=[REL_OBJ_HAS_LINE, REL_SUB_LINE_RELATED_ITEM], subject_entity=self.id):
            relation._delete_without_transaction()

    def _pre_save_clone(self, source):
        self.related_document = source._new_related_document
        self.related_item     = source.related_item

    def clean(self):
        if self.discount_unit == PERCENT_PK:
            if not (0 <= self.discount <= 100):
                raise ValidationError(ugettext(u"If you choose % for your discount unit, your discount must be between 1 and 100%"))
        else: # amount €/$/...
            if self.total_discount: # Global discount
                if self.discount > self.unit_price * self.quantity:
                    raise ValidationError(ugettext(u"Your overall discount is superior than the total line (unit price * quantity)"))
            else: # Unitary discount
                if self.discount > self.unit_price:
                    raise ValidationError(ugettext(u"Your discount is superior than the unit price"))
        if self.related_item:
            if self.on_the_fly_item:
                raise ValidationError(ugettext(u"You cannot set an on the fly name to a line with a related item"))
        else:
            if not self.on_the_fly_item:
                raise ValidationError(ugettext(u"You must define a name for an on the fly item"))
        super(Line, self).clean()

    def clone(self, new_related_document=None):
        #BEWARE: CremeProperty and Relation are not cloned (except our 2 internal relations)
        self._new_related_document = new_related_document or self.related_document

        #return self._clone_object() #NB: it does not copy our 2 internal relations
        return super(Line, self).clone()

    def get_price_inclusive_of_tax(self):
        total_ht = self.get_price_exclusive_of_tax()
        vat_value = self.vat_value
        vat = (total_ht * vat_value.value / 100) if vat_value else 0
        return round_to_2(total_ht + vat)

    def get_raw_price(self):
        return round_to_2(self.quantity * self.unit_price)

    def get_price_exclusive_of_tax(self):
        document                = self.related_document
        discount_document       = document.discount
        discount_line           = self.discount
        global_discount_line    = self.total_discount
        unit_price_line         = self.unit_price

        if self.discount_unit == PERCENT_PK and discount_line:
            if global_discount_line:
                product_qt_up = self.quantity * unit_price_line
                total_after_first_discount = product_qt_up - (product_qt_up * discount_line / 100)
            else:
                total_after_first_discount = self.quantity * (unit_price_line - (unit_price_line * discount_line / 100 ))
        elif global_discount_line:
            total_after_first_discount = self.quantity * unit_price_line - discount_line
        else:
            total_after_first_discount = self.quantity * (unit_price_line - discount_line)

        total_exclusive_of_tax = total_after_first_discount
        if discount_document:
            total_exclusive_of_tax -= total_after_first_discount * discount_document / 100

        return round_to_2(total_exclusive_of_tax)

    def get_related_entity(self): #for generic views & delete
        return self.related_document

    @property
    def related_document(self):
        if not self._related_document:
            #TODO: subject_entity=self.id ?? test with assertNumQueries
            self._related_document = self.relations.get(type=REL_OBJ_HAS_LINE, subject_entity=self.id).object_entity.get_real_entity()

        return self._related_document

    @related_document.setter
    def related_document(self, billing_entity):
        assert self.pk is None, 'Line.related_document(setter): line is already saved (can not change any more).'
        self._related_document = billing_entity

    @property
    def related_item(self):
        if not self._related_item and not self.on_the_fly_item:
            try:
                self._related_item = self.relations.get(type=REL_SUB_LINE_RELATED_ITEM, subject_entity=self.id).object_entity.get_real_entity()
            except Relation.DoesNotExist:
                warn('Line.related_item(): relation does not exist !!')

        return self._related_item

    @related_item.setter
    def related_item(self, entity):
        assert self.pk is None, 'Line.related_item(setter): line is already saved (can not change any more).'
        self._related_item = entity

    @staticmethod
    def get_lv_absolute_url():
        return '/billing/lines'

    def get_verbose_type(self):
        return LINE_TYPES.get(self.type, "")

    def save(self, *args, **kwargs):
        if not self.pk: #creation
            assert self._related_document, 'Line.related_document is required'
            assert bool(self._related_item) ^ bool(self.on_the_fly_item), 'Line.related_item or Line.on_the_fly_item is required'

            self.user = self._related_document.user

            super(Line, self).save(*args, **kwargs)

            create_relation = partial(Relation.objects.create, subject_entity=self, user=self.user)
            create_relation(type_id=REL_OBJ_HAS_LINE, object_entity=self._related_document)

            if self._related_item:
                create_relation(type_id=REL_SUB_LINE_RELATED_ITEM, object_entity=self._related_item)
        else:
            super(Line, self).save(*args, **kwargs)

        #TODO: problem, if several lines are added/edited at once, lots of useless queries (workflow engine ??)
        self.related_document.save() #update totals


#TODO: problem, if several lines are deleted at once, lots of useless queries (workflow engine ??)
@receiver(post_delete, sender=Relation)
def _manage_line_deletion(sender, instance, **kwargs):
    """Invoice calculated totals have to be refreshed"""
    if instance.type_id == REL_OBJ_HAS_LINE:
        instance.object_entity.get_real_entity().save()
