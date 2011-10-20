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

from decimal import Decimal

from django.db.models import CharField, IntegerField, DecimalField, BooleanField, TextField
from django.db.models.fields import PositiveIntegerField
from django.db.models.query_utils import Q
from django.utils.translation import ugettext_lazy as _

from creme_core.models import CremeEntity, Relation
from creme_core.core.function_field import FunctionField

from billing.constants import DEFAULT_VAT, REL_OBJ_HAS_LINE, REL_SUB_LINE_RELATED_ITEM, PERCENT_PK
from billing.utils import round_to_2


default_decimal = Decimal()

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
    quantity        = IntegerField(_(u'Quantity'), blank=False, null=False, default=1)
    unit_price      = DecimalField(_(u'Unit price'), max_digits=10, decimal_places=2, default=default_decimal)
    discount        = DecimalField(_(u'Discount'), max_digits=10, decimal_places=2, default=default_decimal)
    discount_unit   = PositiveIntegerField(_(u'Discount Unit'), blank=True, null=True, default=PERCENT_PK)
    credit          = DecimalField(_(u'Credit'), max_digits=10, decimal_places=2, default=default_decimal)
    total_discount  = BooleanField(_('Total discount ?'))
    vat             = DecimalField(_(u'VAT'), max_digits=4, decimal_places=2, default=DEFAULT_VAT)
    is_paid         = BooleanField(_(u'Paid ?'))
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
        vat = total_ht * self.vat / 100
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

        return round_to_2(total_exclusive_of_tax - self.credit)

    def get_related_entity(self): #for generic views & delete
        return self.related_document

    def _get_related_document(self):
        try:
            return self.relations.get(type=REL_OBJ_HAS_LINE, subject_entity=self.id).object_entity.get_real_entity()#TODO:Cache ?
        except Relation.DoesNotExist:
            return None

    def _set_related_document(self, object_entity):
        Relation.objects.filter(subject_entity=self, type=REL_OBJ_HAS_LINE).delete()#This should be done most of the time by the signal
        #Beware if self, object_entity or self.user have not a pk the relation will not be created
        return Relation.objects.create(object_entity=object_entity, subject_entity=self, type_id=REL_OBJ_HAS_LINE, user=self.user)

    related_document = property(_get_related_document, _set_related_document); del _get_related_document, _set_related_document

    def _get_related_item(self):
        try:
            return self.relations.get(type=REL_SUB_LINE_RELATED_ITEM, subject_entity=self.id).object_entity.get_real_entity()#TODO:Cache ?
        except Relation.DoesNotExist:
            return None

    def _set_related_item(self, object_entity):
        Relation.objects.filter(subject_entity=self, type=REL_SUB_LINE_RELATED_ITEM).delete()#This should be done most of the time by the signal
        #Beware if self, object_entity or self.user have not a pk the relation will not be created
        return Relation.objects.create(object_entity=object_entity, subject_entity=self, type_id=REL_SUB_LINE_RELATED_ITEM, user=self.user)

    related_item = property(_get_related_item, _set_related_item); del _get_related_item, _set_related_item

    @staticmethod
    def get_lv_absolute_url():
        return '/billing/lines'

    def get_verbose_type(self):
        return LINE_TYPES.get(self.type, "")

