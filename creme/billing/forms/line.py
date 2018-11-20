# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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
from functools import partial

from django.db.transaction import atomic
from django.forms import (ModelChoiceField, TypedChoiceField, DecimalField,
        ValidationError, TextInput, Textarea)
from django.utils.translation import ugettext_lazy as _, ugettext

from creme.creme_core import forms as core_forms
from creme.creme_core.forms.fields import MultiCreatorEntityField
from creme.creme_core.models import Relation, Vat

from creme import products
from creme.products.forms.fields import CategoryField

from creme import billing
from .. import constants


ProductLine = billing.get_product_line_model()
ServiceLine = billing.get_service_line_model()


class _LineMultipleAddForm(core_forms.CremeForm):
    quantity       = DecimalField(label=_('Quantity'),
                                  min_value=constants.DEFAULT_DECIMAL,
                                  initial=constants.DEFAULT_QUANTITY,
                                  decimal_places=2,
                                 )
    discount_value = DecimalField(label=_('Discount'),
                                  min_value=constants.DEFAULT_DECIMAL,
                                  max_value=Decimal('100'),
                                  initial=constants.DEFAULT_DECIMAL,
                                  decimal_places=2,
                                  help_text=_('Percentage applied on the unit price'),
                                 )
    vat            = ModelChoiceField(label=_('Vat'), queryset=Vat.objects.all(),
                                      empty_label=None,
                                     )

    def _get_line_class(self):
        raise NotImplementedError

    def __init__(self, entity, *args, **kwargs):
        # super(_LineMultipleAddForm, self).__init__(*args, **kwargs)
        super().__init__(*args, **kwargs)
        self.billing_document = entity
        self.fields['vat'].initial = Vat.get_default_vat()  # Not in field declaration because default value can change

    def save(self):
        cdata = self.cleaned_data
        create_item = partial(self._get_line_class().objects.create,
                              related_document=self.billing_document,
                              quantity=cdata['quantity'],
                              discount=cdata['discount_value'],
                              vat_value=cdata['vat'],
                             )

        for item in cdata['items']:
            create_item(related_item=item,
                        unit_price=item.unit_price,
                        unit=item.unit,
                       )


class ProductLineMultipleAddForm(_LineMultipleAddForm):
    items = MultiCreatorEntityField(label=_('Products'), model=products.get_product_model())

    blocks = core_forms.FieldBlockManager(
        ('general',    _('Products choice'), ['items']),
        ('additional', _('Optional global information applied to your selected products'), ['quantity', 'vat', 'discount_value'])
    )

    def _get_line_class(self):
        return ProductLine


class ServiceLineMultipleAddForm(_LineMultipleAddForm):
    items = MultiCreatorEntityField(label=_('Services'), model=products.get_service_model())

    blocks = core_forms.FieldBlockManager(
        ('general',    _('Services choice'), ['items']),
        ('additional', _('Optional global information applied to your selected services'), ['quantity', 'vat', 'discount_value'])
    )

    def _get_line_class(self):
        return ServiceLine


# NB: model (ie: _meta.model) is set later, because this class is only used as base class
class LineEditForm(core_forms.CremeModelWithUserForm):
    # TODO: we want to disabled CreatorChoiceField ; should we disabled globally this feature with Vat model ??
    vat_value = ModelChoiceField(label=_('Vat'), queryset=Vat.objects.all(),
                                 required=True,  # TODO: remove when null=False in the model
                                 empty_label=None,
                                )

    class Meta:
        exclude = ()

    def __init__(self, user, related_document=None, *args, **kwargs):
        # super(LineEditForm, self).__init__(user=user, *args, **kwargs)
        super().__init__(user=user, *args, **kwargs)
        self.related_document = related_document
        fields = self.fields

        if self.instance.related_item:
            del fields['on_the_fly_item']
        else:
            fields['on_the_fly_item'].widget = TextInput(attrs={'class': 'line-on_the_fly', 'validator': 'Value'})

        fields['unit_price'].widget = TextInput(attrs={'class': 'line-unit_price bound', 'validator': 'Decimal'})
        fields['quantity'].widget   = TextInput(attrs={'class': 'line-quantity bound', 'validator': 'PositiveDecimal'})
        fields['unit'].widget       = TextInput(attrs={'class': 'line-unit'})
        fields['discount'].widget   = TextInput(attrs={'class': 'line-quantity_discount bound'})

        currency_str = related_document.currency.local_symbol
        discount_units = [(constants.DISCOUNT_PERCENT,     '%'),
                          (constants.DISCOUNT_LINE_AMOUNT, _('{currency} per line').format(currency=currency_str)),
                          (constants.DISCOUNT_ITEM_AMOUNT, _('{currency} per unit').format(currency=currency_str)),
                         ]

        line = self.instance
        fields['discount_unit'] = discount_unit_f = TypedChoiceField(choices=discount_units, coerce=int)
        discount_unit_f.initial = constants.DISCOUNT_PERCENT if line.discount_unit == constants.DISCOUNT_PERCENT else \
                                  (constants.DISCOUNT_LINE_AMOUNT if line.total_discount else constants.DISCOUNT_ITEM_AMOUNT) #HACK: see below
        discount_unit_f.required = True
        discount_unit_f.widget.attrs = {'class': 'bound'}

        fields['comment'].widget = Textarea(attrs={'class': 'line-comment', 'rows': 2})
        fields['vat_value'].initial = Vat.get_default_vat()

    # TODO: UGLY HACK: we should have our 3 choices in Line.discount_unit & remove Line.total_discount (refactor the template too)
    def clean(self):
        # cdata = super(LineEditForm, self).clean()
        cdata = super().clean()

        if not self._errors:
            discount_unit = cdata['discount_unit']
            total_discount = False

            if discount_unit == constants.DISCOUNT_LINE_AMOUNT:
                total_discount = True
            elif discount_unit == constants.DISCOUNT_ITEM_AMOUNT:
                discount_unit = constants.DISCOUNT_LINE_AMOUNT
  
            line = self.instance
            line.total_discount = total_discount
            line.discount_unit = discount_unit

        return cdata

    def save(self, *args, **kwargs):
        instance = self.instance

        # handle add on the fly client side js
        if not instance.pk:
            instance.related_document = self.related_document

        # return super(LineEditForm, self).save(*args, **kwargs)
        return super().save(*args, **kwargs)


class AddToCatalogForm(core_forms.CremeForm):
    sub_category = CategoryField(label=_('Sub-category'), required=False)

    def __init__(self, user, line, related_item_class, *args, **kwargs):
        # super(AddToCatalogForm, self).__init__(user, *args, **kwargs)
        super().__init__(user, *args, **kwargs)
        self.line = line
        self.related_item_class = related_item_class

    def clean(self):
        if not self.user.has_perm_to_create(self.related_item_class):
            raise ValidationError(ugettext('You are not allowed to create this entity'),
                                  code='forbidden_creation',
                                 )

        if not self.line.on_the_fly_item:
            raise ValidationError(ugettext('You are not allowed to add this item '
                                           'to the catalog because it is not on the fly'
                                          ),
                                  code='not_on_the_fly',
                                 )

        # return super(AddToCatalogForm, self).clean()
        return super().clean()

    @atomic
    def save(self, *args, **kwargs):
        sub_category = self.cleaned_data['sub_category']
        line = self.line

        # First create the related item...
        item = self.related_item_class.objects.create(name=line.on_the_fly_item,
                                                      user=self.user,
                                                      unit_price=line.unit_price,
                                                      unit=line.unit,
                                                      category=sub_category.category,
                                                      sub_category=sub_category,
                                                     )

        # ..then update the line that is now related to the new created item and not on the fly anymore.
        line.on_the_fly_item = None
        line.save()

        Relation.objects.create(subject_entity=line,
                                type_id=constants.REL_SUB_LINE_RELATED_ITEM,
                                object_entity=item,
                                user=self.user,
                               )
