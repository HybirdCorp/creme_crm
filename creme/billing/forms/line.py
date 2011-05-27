# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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
from django.forms import  BooleanField, ValidationError

from creme_core.forms import CremeEntityForm, FieldBlockManager
from creme_core.forms.fields import CremeEntityField
from creme_core.forms.widgets import ListViewWidget

from products.models import Product, Service
from products.forms.product import ProductCategoryField

from billing.models import ProductLine, ServiceLine, PRODUCT_LINE_TYPE, SERVICE_LINE_TYPE
from billing.constants import DEFAULT_VAT

from creme import form_post_save #TODO: move in creme_core ??


default_decimal = Decimal()


class LineForm(CremeEntityForm):
    blocks = FieldBlockManager(('general', _(u'Line information'), ['related_item', 'comment', 'quantity', 'unit_price',
                                                                    'discount', 'credit', 'total_discount', 'vat', 'user'])
                              )

    class Meta:
        exclude = ('document', 'is_paid')

    def __init__(self, entity, *args, **kwargs):
        super(LineForm, self).__init__(*args, **kwargs)
        self._document = entity #NB: self.document is a related name

    def save(self):
        instance = self.instance
        created = not bool(instance.pk)
        instance.is_paid = False
        super(LineForm, self).save()
        instance.related_document = self._document

        form_post_save.send(sender=self.instance.__class__, instance=self.instance, created=created)

        return instance


class ProductLineForm(LineForm):
    related_item = CremeEntityField(label=_("Product"), model=Product,
                                    widget=ListViewWidget(attrs={'selection_cb':      'creme.billing.lineAutoPopulateSelection',
                                                                 'selection_cb_args': {'attr': 'name', 'values': ['unit_price']},
                                                                }
                                                          )
                                   )

    class Meta:
        model = ProductLine
        exclude = LineForm.Meta.exclude + ('on_the_fly_item',)

    def __init__(self, entity, *args, **kwargs):
        super(ProductLineForm, self).__init__(entity, *args, **kwargs)
        self.instance.type = PRODUCT_LINE_TYPE
        related_item = self.instance.related_item
        if related_item is not None:
            self.fields['related_item'].initial = related_item.id

    def save(self):
        instance = super(ProductLineForm, self).save()
        instance.related_item = self.cleaned_data['related_item']
        return instance


class ProductLineOnTheFlyForm(LineForm):
    has_to_register_as = BooleanField(label=_(u"Save as product ?"), required=False,
                                      help_text=_(u"Here you can save a on-the-fly Product as a true Product ; in this case, category and sub-category are required."))

    sub_category = ProductCategoryField(label=_(u'Sub-category'), required=False)

    blocks = FieldBlockManager(
        ('general',     _(u'Line information'),    ['on_the_fly_item', 'comment', 'quantity', 'unit_price',
                                                    'discount', 'credit', 'total_discount', 'vat', 'user']),
        ('additionnal', _(u'Additional features'), ['has_to_register_as', 'sub_category'])
     )

    class Meta:
        model = ProductLine
        exclude = LineForm.Meta.exclude + ('related_item',)

    def __init__(self, *args, **kwargs):
        super(ProductLineOnTheFlyForm, self).__init__(*args, **kwargs)
        self.instance.type = PRODUCT_LINE_TYPE

        if self.instance.pk is not None:
            self.blocks = FieldBlockManager(
                    ('general', ugettext(u'Line information'), ['on_the_fly_item', 'comment', 'quantity', 'unit_price',
                                                                'discount', 'credit', 'total_discount', 'vat', 'user']),
                )
        elif not self.user.has_perm_to_create(Product):
            fields = self.fields
            has_to_register_as = fields['has_to_register_as']
            has_to_register_as.help_text = ugettext(u'You are not allowed to create Products')
            has_to_register_as.widget.attrs     = {'disabled': True}
            fields['sub_category'].widget.attrs = {'disabled': True}

    def clean_has_to_register_as(self):
        create_product = self.cleaned_data.get('has_to_register_as', False)

        if create_product and not self.user.has_perm_to_create(Product):
            raise ValidationError(ugettext(u'You are not allowed to create Products'))

        return create_product

    def clean(self):
        cleaned_data = self.cleaned_data
        get_data     = cleaned_data.get

        #TODO: use has_key() ??
        if get_data('has_to_register_as'):
            sub_category = get_data('sub_category')
            if sub_category is None:
                raise ValidationError(ugettext(u'Sub-category is required if you want to save as a true product.'))

            if sub_category.category is None:
                raise ValidationError(ugettext(u'Category is required if you want to save as a true product.'))

        return cleaned_data

    def save(self):
        get_data = self.cleaned_data.get

        if get_data('has_to_register_as'):
            sub_category = get_data('sub_category')

            product = Product.objects.create(name=get_data('on_the_fly_item', ''),
                                             user=get_data('user'),
                                             code=0,
                                             unit_price=get_data('unit_price', 0),
                                             category=sub_category.category,
                                             sub_category=sub_category,
                                            )

            plcf = ProductLineForm(entity=self._document, user=self.user,
                                   data={
                                          'related_item':   '%s,' % product.pk,
                                          'quantity':       get_data('quantity', 0),
                                          'unit_price':     get_data('unit_price', default_decimal),
                                          'credit':         get_data('credit', default_decimal),
                                          'discount':       get_data('discount', default_decimal),
                                          'total_discount': get_data('total_discount', False),
                                          'vat':            get_data('vat', DEFAULT_VAT),
                                          'user':           product.user_id,
                                          'comment':        get_data('comment', '')
                                        }
                                  )

            if plcf.is_valid():
                instance = plcf.save()
        else:
            instance = super(ProductLineOnTheFlyForm, self).save()

        return instance


class ServiceLineForm(LineForm):
    related_item = CremeEntityField(label=_("Service"), model=Service,
                                    widget=ListViewWidget(attrs={'selection_cb':      'creme.billing.lineAutoPopulateSelection',
                                                                 'selection_cb_args': {'attr': 'name', 'values': ['unit_price']},
                                                                }
                                                         )
                                   )

    class Meta:
        model = ServiceLine
        exclude = LineForm.Meta.exclude + ('on_the_fly_item',)

    def __init__(self, entity, *args, **kwargs):
        super(ServiceLineForm, self).__init__(entity, *args, **kwargs)
        self.instance.type = SERVICE_LINE_TYPE
        related_item = self.instance.related_item
        if related_item is not None:
            self.fields['related_item'].initial = related_item.id

    def save(self):
        instance = super(ServiceLineForm, self).save()
        instance.related_item = self.cleaned_data['related_item']
        return instance


class ServiceLineOnTheFlyForm(LineForm):
    has_to_register_as = BooleanField(label=_(u"Save as service ?"), required=False,
                                      help_text=_(u"Here you can save a on-the-fly Service as a true Service ; in this case, category is required."))

    sub_category = ProductCategoryField(label=_(u'Sub-category'), required=False)

    blocks = FieldBlockManager(
        ('general',     _(u'Line information'),    ['on_the_fly_item', 'comment', 'quantity', 'unit_price',
                                                    'discount', 'credit', 'total_discount', 'vat', 'user']),
        ('additionnal', _(u'Additional features'), ['has_to_register_as','sub_category'])
     )

    class Meta:
        model = ServiceLine
        exclude = LineForm.Meta.exclude + ('related_item',)

    def __init__(self, *args, **kwargs):
        super(ServiceLineOnTheFlyForm, self).__init__(*args, **kwargs)
        self.instance.type = SERVICE_LINE_TYPE

        if self.instance.pk is not None:
            #TODO: remove the block 'additionnal' instead ??
            self.blocks = FieldBlockManager(
                    ('general', _(u'Line information'), ['on_the_fly_item', 'comment', 'quantity', 'unit_price',
                                                         'discount', 'credit', 'total_discount', 'vat', 'user']),
                )
        elif not self.user.has_perm_to_create(Service):
            fields = self.fields
            has_to_register_as = fields['has_to_register_as']
            has_to_register_as.help_text = ugettext(u'You are not allowed to create Services')
            has_to_register_as.widget.attrs = {'disabled': True}
            fields['sub_category'].widget.attrs = {'disabled': True}

    def clean_has_to_register_as(self):
        create_service = self.cleaned_data.get('has_to_register_as', False)

        if create_service and not self.user.has_perm_to_create(Service):
            raise ValidationError(ugettext(u'You are not allowed to create Services'))

        return create_service

    def clean(self):
        cleaned_data = self.cleaned_data
        get_data     = cleaned_data.get

        #TODO: use has_key() ??
        if get_data('has_to_register_as'):
            sub_category = get_data('sub_category')
            if sub_category is None:
                raise ValidationError(ugettext(u'Sub-category is required if you want to save as a true service.'))

            if sub_category.category is None:
                raise ValidationError(ugettext(u'Category is required if you want to save as a true service.'))

        return cleaned_data

    def save(self):
        get_data = self.cleaned_data.get

        if get_data('has_to_register_as'):
            sub_category = get_data('sub_category')

            service = Service.objects.create(name=get_data('on_the_fly_item', ''),
                                             user=get_data('user'),
                                             reference='',
                                             category=sub_category.category,
                                             sub_category=sub_category,
                                             unit_price=get_data('unit_price', 0),
                                            )

            slcf = ServiceLineForm(entity=self._document, user=self.user,
                                   data={
                                          'related_item':   '%s,' % service.pk,
                                          'quantity':       get_data('quantity', 0),
                                          'unit_price':     get_data('unit_price', default_decimal),
                                          'credit':         get_data('credit', default_decimal),
                                          'discount':       get_data('discount', default_decimal),
                                          'total_discount': get_data('total_discount', False),
                                          'vat':            get_data('vat', DEFAULT_VAT),
                                          'user':           service.user_id,
                                          'comment':        get_data('comment', ''),
                                        }
                                  )

            if slcf.is_valid():
                instance = slcf.save()
        else:
            instance = super(ServiceLineOnTheFlyForm, self).save()

        return instance
