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

from decimal import Decimal
from functools import partial

from django import forms
from django.core.exceptions import ValidationError
from django.db.transaction import atomic
from django.forms.formsets import formset_factory
from django.forms.models import BaseModelFormSet, modelform_factory
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme import billing, products
from creme.creme_core import forms as core_forms
from creme.creme_core.forms.fields import MultiCreatorEntityField
from creme.creme_core.forms.widgets import CremeTextarea
from creme.creme_core.models import Relation, Vat
from creme.products.forms.fields import CategoryField

from .. import constants

ProductLine = billing.get_product_line_model()
ServiceLine = billing.get_service_line_model()


class _LineMultipleAddForm(core_forms.CremeForm):
    quantity = forms.DecimalField(
        label=_('Quantity'),
        min_value=constants.DEFAULT_DECIMAL,
        initial=constants.DEFAULT_QUANTITY,
        decimal_places=2,
    )
    discount_value = forms.DecimalField(
        label=_('Discount'),
        min_value=constants.DEFAULT_DECIMAL,
        max_value=Decimal('100'),
        initial=constants.DEFAULT_DECIMAL,
        decimal_places=2,
        help_text=_('Percentage applied on the unit price'),
    )
    vat = forms.ModelChoiceField(
        label=_('Vat'), queryset=Vat.objects.all(), empty_label=None,
    )

    def _get_line_class(self):
        raise NotImplementedError

    def __init__(self, entity, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.billing_document = entity
        # Not in field declaration because default value can change
        # self.fields['vat'].initial = Vat.get_default_vat()
        self.fields['vat'].initial = Vat.objects.default()

    def save(self):
        cdata = self.cleaned_data
        create_item = partial(
            self._get_line_class().objects.create,
            related_document=self.billing_document,
            quantity=cdata['quantity'],
            discount=cdata['discount_value'],
            vat_value=cdata['vat'],
        )

        for item in cdata['items']:
            create_item(
                related_item=item, unit_price=item.unit_price, unit=item.unit,
            )


class ProductLineMultipleAddForm(_LineMultipleAddForm):
    items = MultiCreatorEntityField(label=_('Products'), model=products.get_product_model())

    blocks = core_forms.FieldBlockManager(
        {
            'id': 'general',
            'label': _('Products choice'),
            'fields': ['items'],
        }, {
            'id': 'additional',
            'label': _('Optional global information applied to your selected products'),
            'fields': ['quantity', 'vat', 'discount_value'],
        },
    )

    def _get_line_class(self):
        return ProductLine


class ServiceLineMultipleAddForm(_LineMultipleAddForm):
    items = MultiCreatorEntityField(label=_('Services'), model=products.get_service_model())

    blocks = core_forms.FieldBlockManager(
        {
            'id': 'general',
            'label': _('Services choice'),
            'fields': ['items'],
        }, {
            'id': 'additional',
            'label': _('Optional global information applied to your selected services'),
            'fields': ['quantity', 'vat', 'discount_value'],
        },
    )

    def _get_line_class(self):
        return ServiceLine


# NB: model (ie: _meta.model) is set later, because this class is only used as base class
class LineEditForm(core_forms.CremeModelForm):
    # TODO: we want to disabled CreatorChoiceField ;
    #       should we disabled globally this feature with Vat model ??
    vat_value = forms.ModelChoiceField(
        label=_('Vat'), queryset=Vat.objects.all(), empty_label=None,
    )

    class Meta:
        exclude = ()
        widgets = {
            'on_the_fly_item': forms.TextInput(
                attrs={'class': 'line-on_the_fly', 'validator': 'Value'},
            ),
            'unit_price': forms.TextInput(
                attrs={'class': 'line-unit_price bound', 'validator': 'Decimal'},
            ),
            'quantity': forms.TextInput(
                attrs={'class': 'line-quantity bound', 'validator': 'PositiveDecimal'},
            ),
            'unit': forms.TextInput(attrs={'class': 'line-unit'}),
            'discount': forms.TextInput(attrs={'class': 'line-quantity_discount bound'}),
            'comment': CremeTextarea(attrs={'class': 'line-comment', 'rows': 2}),
        }

    # TODO: related_document=None ??
    def __init__(self, user, related_document=None, *args, **kwargs):
        super().__init__(user=user, *args, **kwargs)
        self.related_document = related_document
        fields = self.fields

        if self.instance.related_item:
            del fields['on_the_fly_item']

        Discount = self._meta.model.Discount

        currency_str = related_document.currency.local_symbol
        discount_units = [
            # (constants.DISCOUNT_PERCENT, '%'),
            (Discount.PERCENT, '%'),
            (
                # constants.DISCOUNT_LINE_AMOUNT,
                Discount.LINE_AMOUNT,
                gettext('{currency} per line').format(currency=currency_str),
            ),
            (
                # constants.DISCOUNT_ITEM_AMOUNT,
                Discount.ITEM_AMOUNT,
                gettext('{currency} per unit').format(currency=currency_str),
            ),
        ]

        discount_unit_f = fields['discount_unit']
        discount_unit_f.choices = discount_units
        discount_unit_f.widget.attrs = {'class': 'bound'}

        # fields['vat_value'].initial = Vat.get_default_vat()
        fields['vat_value'].initial = Vat.objects.default()

    def save(self, *args, **kwargs):
        instance = self.instance

        # handle add on the fly client side js
        if not instance.pk:
            instance.related_document = self.related_document

        return super().save(*args, **kwargs)


class AddToCatalogForm(core_forms.CremeForm):
    sub_category = CategoryField(label=_('Sub-category'), required=False)

    error_messages = {
        'forbidden_creation': _('You are not allowed to create this entity'),
        'not_on_the_fly': _(
            'You are not allowed to add this item '
            'to the catalog because it is not on the fly'
        ),
    }

    def __init__(self, user, line, related_item_class, *args, **kwargs):
        super().__init__(user, *args, **kwargs)
        self.line = line
        self.related_item_class = related_item_class

    def clean(self):
        if not self.user.has_perm_to_create(self.related_item_class):
            raise ValidationError(
                self.error_messages['forbidden_creation'],
                code='forbidden_creation',
            )

        if not self.line.on_the_fly_item:
            raise ValidationError(
                self.error_messages['not_on_the_fly'],
                code='not_on_the_fly',
            )

        return super().clean()

    @atomic
    def save(self, *args, **kwargs):
        sub_category = self.cleaned_data['sub_category']
        line = self.line

        # First create the related item...
        item = self.related_item_class.objects.create(
            name=line.on_the_fly_item,
            user=self.user,
            unit_price=line.unit_price,
            unit=line.unit,
            category=sub_category.category,
            sub_category=sub_category,
        )

        # ...then update the line that is now related to the new created item
        # and not on the fly anymore.
        line.on_the_fly_item = None
        line.save()

        Relation.objects.create(
            subject_entity=line,
            type_id=constants.REL_SUB_LINE_RELATED_ITEM,
            object_entity=item,
            user=self.user,
        )


class BaseLineEditFormset(formset_factory(core_forms.CremeModelForm, formset=BaseModelFormSet)):
    model = None
    base_form_class = LineEditForm
    extra = 0
    can_delete = True

    def __init__(self, model, user, related_document=None, **kwargs):
        self.model = model
        self.user = user
        self.related_document = related_document
        # handle prefix here ?
        super().__init__(**kwargs)
        self.form_class = modelform_factory(model, form=self.get_form_class())

    def get_form_class(self):
        return self.base_form_class

    def form(self, **kwargs):
        return self.form_class(
            self.user,
            related_document=self.related_document,
            **kwargs)
