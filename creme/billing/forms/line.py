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

from django.utils.translation import ugettext_lazy as _, ugettext
from django.forms import IntegerField, BooleanField, ModelChoiceField, Select, ValidationError

from creme_core.forms import CremeModelWithUserForm, FieldBlockManager
from creme_core.forms.fields import CremeEntityField
from creme_core.forms.widgets import ListViewWidget, DependentSelect

from products.models import Product, Service, Category, SubCategory, ServiceCategory

from billing.models import ProductLine, ServiceLine
from billing.constants import DEFAULT_VAT

from creme import form_post_save #TODO: move in creme_core ??


default_decimal = Decimal()


class LineCreateForm(CremeModelWithUserForm):
    blocks = FieldBlockManager(('general', _(u'Line information'), ['related_item', 'comment', 'quantity', 'unit_price',
                                                                    'discount', 'credit', 'total_discount', 'vat', 'user'])
                              )

    class Meta:
        exclude = ('document', 'is_paid')

    def __init__(self, entity, *args, **kwargs):
        super(LineCreateForm, self).__init__(*args, **kwargs)
        self.document = entity

    def save(self):
        instance = self.instance
        created = not bool(instance.pk)
        instance.document = self.document
        instance.is_paid = False
        super(LineCreateForm, self).save()

        form_post_save.send(sender=self.instance.__class__, instance=self.instance, created=created)

        return instance


class ProductLineCreateForm(LineCreateForm):
    related_item = CremeEntityField(label=_("Product"), model=Product,
                                    widget=ListViewWidget(attrs={'selection_cb':'creme.product_line.auto_populate_selection','selection_cb_args':{'attr':'name','values':['unit_price']}}))

    class Meta:
        model = ProductLine
        exclude = LineCreateForm.Meta.exclude + ('on_the_fly_item',)


class ProductLineOnTheFlyCreateForm(LineCreateForm):
    has_to_register_as = BooleanField(label=_(u"Save as product ?"), required=False,
                                      help_text=_(u"Here you can save a on-the-fly Product as a true Product ; in this case, category and sub-category are required."))
    category           = ModelChoiceField(queryset=Category.objects.all(), label=_(u'Category'),
                                          widget=DependentSelect(target_id='id_sub_category',
                                          target_url='/products/sub_category/load'),
                                          required=False)
    sub_category       = ModelChoiceField(queryset=SubCategory.objects.all(),
                                          label=_(u'Sub-category'),
                                          widget=Select(attrs={'id': 'id_sub_category'}),
                                          required=False)

    blocks = FieldBlockManager(
        ('general',     _(u'Line information'),    ['on_the_fly_item', 'comment', 'quantity', 'unit_price',
                                                    'discount', 'credit', 'total_discount', 'vat', 'user']),
        ('additionnal', _(u'Additional features'), ['has_to_register_as', 'category', 'sub_category'])
     )

    class Meta:
        model = ProductLine
        exclude = LineCreateForm.Meta.exclude + ('related_item',)

    def __init__(self, *args, **kwargs):
        super(ProductLineOnTheFlyCreateForm, self).__init__(*args, **kwargs)

        if self.instance.pk is not None:
            self.blocks = FieldBlockManager(
                    ('general', ugettext(u'Line information'), ['on_the_fly_item', 'comment', 'quantity', 'unit_price',
                                                                'discount', 'credit', 'total_discount', 'vat', 'user']),
                )

    def clean(self):
        cleaned_data = self.cleaned_data
        get_data     = cleaned_data.get

        #TODO: use has_key() ??
        if get_data('has_to_register_as'):
            if get_data('category') is None:
                raise ValidationError(ugettext(u'Category is required if you want to save as a true product.'))
            elif get_data('sub_category') is None:
                raise ValidationError(ugettext(u'Sub-category is required if you want to save as a true product.'))

        return cleaned_data

    def save(self):
        get_data = self.cleaned_data.get

        if get_data('has_to_register_as'):
            product = Product.objects.create(name=get_data('on_the_fly_item', ''),
                                             user=get_data('user'),
                                             code=0,
                                             unit_price=get_data('unit_price', 0),
                                             category=get_data('category', 0),
                                             sub_category=get_data('sub_category', 0),
                                            )

            plcf = ProductLineCreateForm(self.document,
                                         {
                                            'related_item':   '%s,' % product.pk,
                                            'quantity':       get_data('quantity', 0),
                                            'unit_price':     get_data('unit_price', default_decimal),
                                            'credit':         get_data('credit', default_decimal),
                                            'discount':       get_data('discount', default_decimal),
                                            'total_discount': get_data('total_discount', False),
                                            'vat':            get_data('vat', DEFAULT_VAT),
                                            'user':           product.user_id,
                                            'comment':        get_data('comment', '')
                                        })

            if plcf.is_valid():
                instance = plcf.save()
        else:
            instance = super(ProductLineOnTheFlyCreateForm, self).save()

        return instance


class ServiceLineCreateForm(LineCreateForm):
    related_item = CremeEntityField(label=_("Service"), model=Service, widget=ListViewWidget(attrs={'selection_cb':'creme.product_line.auto_populate_selection','selection_cb_args':{'attr':'name','values':['unit_price']}}))
    #selection_cb uses the same callback than ProductLineCreateForm so is there no Product line block on the Service line block page => Error. Implements its onw function when it'll be necessary

    class Meta:
        model = ServiceLine
        exclude = LineCreateForm.Meta.exclude + ('on_the_fly_item',)


class ServiceLineOnTheFlyCreateForm(LineCreateForm):
    has_to_register_as = BooleanField(label=_(u"Save as service ?"), required=False,
                                      help_text=_(u"Here you can save a on-the-fly Service as a true Service ; in this case, category is required."))
    category           = ModelChoiceField(queryset=ServiceCategory.objects.all(), label=_(u'Service category'),
                                          required=False)

    blocks = FieldBlockManager(
        ('general',     _(u'Line information'),    ['on_the_fly_item', 'comment', 'quantity', 'unit_price',
                                                    'discount', 'credit', 'total_discount', 'vat', 'user']),
        ('additionnal', _(u'Additional features'), ['has_to_register_as','category'])
     )

    class Meta:
        model = ServiceLine
        exclude = LineCreateForm.Meta.exclude + ('related_item',)

    def __init__(self, *args, **kwargs):
        super(ServiceLineOnTheFlyCreateForm, self).__init__(*args, **kwargs)

        if self.instance.pk is not None:
            #TODO: remove the block 'additionnal' instead ??
            self.blocks = FieldBlockManager(
                    ('general', _(u'Line information'), ['on_the_fly_item', 'comment', 'quantity', 'unit_price',
                                                         'discount', 'credit', 'total_discount', 'vat', 'user']),
                )

    def clean(self):
        cleaned_data = self.cleaned_data
        get_data = cleaned_data.get

        if get_data('has_to_register_as') and get_data('category') is None:
            raise ValidationError(ugettext(u'Category is required if you want to save as a true service.'))

        return cleaned_data

    def save(self):
        get_data = self.cleaned_data.get

        if get_data('has_to_register_as'):
            service = Service.objects.create(name=get_data('on_the_fly_item', ''),
                                             user=get_data('user'),
                                             reference='',
                                             category=get_data('category'),
                                             unit_price=get_data('unit_price', 0),
                                            )

            slcf = ServiceLineCreateForm(self.document,
                                         {
                                            'related_item':   '%s,' % service.pk,
                                            'quantity':       get_data('quantity', 0),
                                            'unit_price':     get_data('unit_price', default_decimal),
                                            'credit':         get_data('credit', default_decimal),
                                            'discount':       get_data('discount', default_decimal),
                                            'total_discount': get_data('total_discount', False),
                                            'vat':            get_data('vat', DEFAULT_VAT),
                                            'user':           service.user_id,
                                            'comment':        get_data('comment', ''),
                                         })

            if slcf.is_valid():
                instance = slcf.save()
        else:
            instance = super(ServiceLineOnTheFlyCreateForm, self).save()

        return instance
