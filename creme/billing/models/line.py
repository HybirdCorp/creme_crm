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
from logging import debug

from django.db.models import CharField, IntegerField, DecimalField, BooleanField, TextField, ForeignKey, PositiveIntegerField
from django.db.models.query_utils import Q
from django.utils.translation import ugettext_lazy as _

from creme_core.models import CremeEntity, Relation
from creme_core.core.function_field import FunctionField

from billing.models.other_models import Vat
from billing.constants import REL_OBJ_HAS_LINE, REL_SUB_LINE_RELATED_ITEM, PERCENT_PK
from billing.utils import round_to_2


default_decimal = Decimal()
default_quantity = Decimal('1.00')

PRODUCT_LINE_TYPE = 1
SERVICE_LINE_TYPE = 2

LINE_TYPES = {
    PRODUCT_LINE_TYPE: _(u"Product"),
    SERVICE_LINE_TYPE: _(u"Service")
}

class _LineTypeField(FunctionField):
    name         = "get_verbose_type"
    verbose_name = _(u'Line type')
    has_filter   = True
    choices      = LINE_TYPES.items()

    @classmethod
    def filter_in_result(cls, search_string):
        return Q(type=search_string)


class Line(CremeEntity):
    on_the_fly_item = CharField(_(u'On-the-fly line'), max_length=100, blank=False, null=True)
    comment         = TextField(_('Comment'), blank=True, null=True)
#    quantity        = IntegerField(_(u'Quantity'), blank=False, null=False, default=1)
    quantity        = DecimalField(_(u'Quantity'), max_digits=10, decimal_places=2, default=default_quantity)
    unit_price      = DecimalField(_(u'Unit price'), max_digits=10, decimal_places=2, default=default_decimal)
    discount        = DecimalField(_(u'Discount'), max_digits=10, decimal_places=2, default=default_decimal)
    discount_unit   = PositiveIntegerField(_(u'Discount Unit'), blank=True, null=True, default=PERCENT_PK)
#    credit          = DecimalField(_(u'Credit'), max_digits=10, decimal_places=2, default=default_decimal)
    total_discount  = BooleanField(_('Total discount ?'))
#    vat             = DecimalField(_(u'VAT'), max_digits=4, decimal_places=2, default=DEFAULT_VAT)
    vat_value       = ForeignKey(Vat, verbose_name=_(u'VAT'), blank=True, null=True)
#    is_paid         = BooleanField(_(u'Paid ?'))
    type            = IntegerField(_(u'Type'), blank=False, null=False, choices=LINE_TYPES.items(), editable=False)

    excluded_fields_in_html_output = CremeEntity.excluded_fields_in_html_output + ['type']
    header_filter_exclude_fields   = CremeEntity.header_filter_exclude_fields + ['type']
    function_fields = CremeEntity.function_fields.new(_LineTypeField())

    class Meta:
        app_label = 'billing'
        verbose_name = _(u'Line')
        verbose_name_plural = _(u'Lines')

    def _pre_delete(self):
        for relation in Relation.objects.filter(type__in=[REL_OBJ_HAS_LINE, REL_SUB_LINE_RELATED_ITEM], subject_entity=self):
            relation._delete_without_transaction()

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

        if discount_document:
            total_exclusive_of_tax = total_after_first_discount - (total_after_first_discount * discount_document / 100)
        else:
            total_exclusive_of_tax = total_after_first_discount

        return round_to_2(total_exclusive_of_tax)

    def get_related_entity(self): #for generic views & delete
        return self.related_document

    @property
    def related_document(self):
        if not self.pk:
            debug('Line.related_document(getter): line not saved yet.')
            return None

        try:
            return self.relations.get(type=REL_OBJ_HAS_LINE, subject_entity=self.id).object_entity.get_real_entity()#TODO:Cache ?
        except Relation.DoesNotExist:
            return None

    @related_document.setter
    def related_document(self, object_entity):
        assert self.pk, 'Line.related_document(setter): line not saved yet.'
        Relation.objects.filter(subject_entity=self, type=REL_OBJ_HAS_LINE).delete()#This should be done most of the time by the signal
        #Beware if self, object_entity or self.user have not a pk the relation will not be created
        return Relation.objects.create(object_entity=object_entity, subject_entity=self, type_id=REL_OBJ_HAS_LINE, user=self.user)

    @property
    def related_item(self):
        if not self.pk:
            debug('Line.related_item(getter): line not saved yet.')
            return None

        try:
            return self.relations.get(type=REL_SUB_LINE_RELATED_ITEM, subject_entity=self.id).object_entity.get_real_entity()#TODO:Cache ?
        except Relation.DoesNotExist:
            return None

    @related_item.setter
    def related_item(self, object_entity):
        assert self.pk, 'Line.related_item(setter): line not saved yet.'
        Relation.objects.filter(subject_entity=self, type=REL_SUB_LINE_RELATED_ITEM).delete()#This should be done most of the time by the signal
        #Beware if self, object_entity or self.user have not a pk the relation will not be created
        return Relation.objects.create(object_entity=object_entity, subject_entity=self, type_id=REL_SUB_LINE_RELATED_ITEM, user=self.user)

    @staticmethod
    def get_lv_absolute_url():
        return '/billing/lines'

    def get_verbose_type(self):
        return LINE_TYPES.get(self.type, "")

    @staticmethod
    def is_discount_valid(unit_price, quantity, discount_value, discount_unit, discount_type):
        if discount_unit == PERCENT_PK:
#            if discount_value < 0 or discount_value > 100:
            if not (0 <= discount_value <= 100):
                return False
        else: # amount �/$/...
            #TODO: factorise "if discount_type"
            if discount_type and discount_value > unit_price * quantity: # Global discount 
                return False
            if not discount_type and discount_value > unit_price: # Unitary discount
                return False

        return True

    @staticmethod
    def generate_lines(klass, item, document, user, optional_infos_map=None):
        new_line = klass()

        new_line.unit_price = item.unit_price
        new_line.user       = user

        if optional_infos_map:
            new_line.quantity = optional_infos_map['quantity']
            new_line.discount = optional_infos_map['discount_value']
            new_line.vat_value = optional_infos_map['vat_value']
        else:
            new_line.vat_value  = Vat.get_default_vat()

        new_line.save()

        new_line.related_item     = item
        new_line.related_document = document

