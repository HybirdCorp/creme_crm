# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2015  Hybird
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

from django.db.transaction import atomic
from django.forms import (ModelChoiceField, TypedChoiceField, DecimalField,
        ValidationError, TextInput, Textarea)
from django.utils.translation import ugettext_lazy as _, ugettext

from creme.creme_core.forms import CremeForm, FieldBlockManager, CremeModelWithUserForm
from creme.creme_core.forms.fields import MultiCreatorEntityField
from creme.creme_core.forms.validators import validate_linkable_entities
from creme.creme_core.models import Relation, Vat

from creme.products import get_service_model, get_product_model
from creme.products.forms.fields import CategoryField

from .. import get_service_line_model, get_product_line_model
from ..constants import (REL_SUB_LINE_RELATED_ITEM, DEFAULT_DECIMAL, DEFAULT_QUANTITY,
        DISCOUNT_PERCENT, DISCOUNT_LINE_AMOUNT, DISCOUNT_ITEM_AMOUNT)
#from ..models import ProductLine, ServiceLine #Line


ProductLine = get_product_line_model()
ServiceLine = get_service_line_model()


class _LineMultipleAddForm(CremeForm):
    quantity       = DecimalField(label=_(u"Quantity"), min_value=DEFAULT_DECIMAL,
                                  initial=DEFAULT_QUANTITY, decimal_places=2,
                                 )
    discount_value = DecimalField(label=_(u"Discount"),
                                  min_value=DEFAULT_DECIMAL, max_value=Decimal('100'),
                                  initial=DEFAULT_DECIMAL, decimal_places=2,
                                  help_text=_(u'Percentage applied on the unit price'),
                                 )
    vat            = ModelChoiceField(label=_(u"Vat"), queryset=Vat.objects.all(),
                                      empty_label=None,
                                     )

    def _get_line_class(self):
        raise NotImplementedError

    def __init__(self, entity, *args, **kwargs):
        super(_LineMultipleAddForm, self).__init__(*args, **kwargs)
        self.billing_document = entity
        self.fields['vat'].initial = Vat.get_default_vat() #not in field declaration because default value can change

    def clean_items(self):
        return validate_linkable_entities(self.cleaned_data['items'], self.user)

    def save(self):
        cleaned_data = self.cleaned_data

        for item in cleaned_data['items']:
            self._get_line_class().objects.create(related_item=item,
                                                  related_document=self.billing_document,
                                                  unit_price=item.unit_price,
                                                  unit=item.unit,
                                                  quantity=cleaned_data['quantity'],
                                                  discount=cleaned_data['discount_value'],
                                                  vat_value=cleaned_data['vat'],
                                                 )


class ProductLineMultipleAddForm(_LineMultipleAddForm):
    items = MultiCreatorEntityField(label=_(u'Products'), model=get_product_model())

    blocks = FieldBlockManager(
        ('general',     _(u'Products choice'), ['items']),
        ('additionnal', _(u'Optional global information applied to your selected products'), ['quantity', 'vat', 'discount_value'])
    )

    def _get_line_class(self):
        return ProductLine


class ServiceLineMultipleAddForm(_LineMultipleAddForm):
    items = MultiCreatorEntityField(label=_(u'Services'), model=get_service_model())

    blocks = FieldBlockManager(
        ('general',     _(u'Services choice'), ['items']),
        ('additionnal', _(u'Optional global information applied to your selected services'), ['quantity', 'vat', 'discount_value'])
    )

    def _get_line_class(self):
        return ServiceLine


# NB: model (ie: _meta.model) is set later, because this class is only used as base class
class LineEditForm(CremeModelWithUserForm):
    # TODO: we want to disabled CreatorChoiceField ; should we disabled globally this feature with Vat model ??
    vat_value = ModelChoiceField(label=_(u"Vat"), queryset=Vat.objects.all(),
                                 required=True, #TODO: remove when null=False in the model
                                 empty_label=None,
                                )

    class Meta:
        #exclude = ('total_discount', 'discount_unit') #todo: remove when total_discount is removed from Line..
        exclude = ()

    def __init__(self, user, related_document=None, *args, **kwargs):
        super(LineEditForm, self).__init__(user=user, *args, **kwargs)
        self.related_document = related_document
        fields = self.fields

        fields['on_the_fly_item'].widget = TextInput(attrs={'class': 'line-on_the_fly', 'validator': 'Value'})

        fields['unit_price'].widget = TextInput(attrs={'class': 'line-unit_price bound', 'validator': 'Decimal'})
        fields['quantity'].widget = TextInput(attrs={'class': 'line-quantity bound', 'validator': 'PositiveDecimal'})
        fields['unit'].widget = TextInput(attrs={'class': 'line-unit'})
        fields['discount'].widget = TextInput(attrs={'class': 'line-quantity_discount bound'})
        #fields['discount_unit'].widget.attrs = fields['total_discount'].widget.attrs = {'class': 'bound'}
        #fields['discount_unit'].required = True

        currency_str = related_document.currency.local_symbol
        discount_units = [(DISCOUNT_PERCENT,        '%'), #_(u"Percent")
                          (DISCOUNT_LINE_AMOUNT,    _(u"%s per line") % currency_str),
                          (DISCOUNT_ITEM_AMOUNT,    _(u"%s per unit") % currency_str),
                         ]

        line = self.instance
        fields['discount_unit'] = discount_unit_f = TypedChoiceField(choices=discount_units, coerce=int)
        discount_unit_f.initial = DISCOUNT_PERCENT if line.discount_unit == DISCOUNT_PERCENT else \
                                  (DISCOUNT_LINE_AMOUNT if line.total_discount else DISCOUNT_ITEM_AMOUNT) #HACK: see below
        discount_unit_f.required = True
        discount_unit_f.widget.attrs = {'class': 'bound'}

        fields['comment'].widget = Textarea(attrs={'class': 'line-comment', 'rows': 2})

        #vat_f = fields['vat_value']
        #vat_f.initial = Vat.get_default_vat()
        #vat_f.required = True
        fields['vat_value'].initial = Vat.get_default_vat()

    # TODO: UGLY HACK: we should have our 3 choices in Line.discount_unit & remove Line.total_discount (refactor the template too)
    def clean(self):
        cdata = super(LineEditForm, self).clean()

        if not self._errors:
            discount_unit = cdata['discount_unit']
            total_discount = False

            if discount_unit == DISCOUNT_LINE_AMOUNT:
                total_discount = True
            elif discount_unit == DISCOUNT_ITEM_AMOUNT:
                discount_unit = DISCOUNT_LINE_AMOUNT
  
            line = self.instance
            line.total_discount = total_discount
            line.discount_unit = discount_unit

        return cdata

    def save(self, *args, **kwargs):
        instance = self.instance

        # handle add on the fly client side js
        if not instance.pk:
            instance.related_document = self.related_document

        return super(LineEditForm, self).save(*args, **kwargs)


class AddToCatalogForm(CremeForm):
    sub_category = CategoryField(label=_(u'Sub-category'), required=False)

    def __init__(self, user, line, related_item_class, *args, **kwargs):
        super(AddToCatalogForm, self).__init__(user, *args, **kwargs)
        self.line = line
        self.related_item_class = related_item_class

    def clean(self):
        if not self.user.has_perm_to_create(self.related_item_class):
            raise ValidationError(ugettext(u'You are not allowed to create this entity'),
                                  code='forbidden_creation',
                                 )

        if not self.line.on_the_fly_item:
            raise ValidationError(ugettext(u'You are not allowed to add this item '
                                           u'to the catalog because it is not on the fly'
                                          ),
                                  code='not_on_the_fly',
                                 )

        return super(AddToCatalogForm, self).clean()

    @atomic
    def save(self, *args, **kwargs):
        sub_category = self.cleaned_data['sub_category']
        line = self.line

        # first create the related item
        item = self.related_item_class.objects.create(name=line.on_the_fly_item,
                                                      user=self.user,
                                                      unit_price=line.unit_price,
                                                      unit=line.unit,
                                                      category=sub_category.category,
                                                      sub_category=sub_category,
                                                     )

        # then update the line that is now related to the new created item and not on the fly any more
        line.on_the_fly_item = None
        line.save()

        Relation.objects.create(subject_entity=line,
                                type_id=REL_SUB_LINE_RELATED_ITEM,
                                object_entity=item,
                                user=self.user,
                               )
