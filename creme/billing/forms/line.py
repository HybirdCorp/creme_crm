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

from django.utils.translation import ugettext_lazy as _
from django.forms import IntegerField, BooleanField, ModelChoiceField, Select, ValidationError
from django.forms.widgets import HiddenInput

from creme_core.forms import CremeModelForm, FieldBlockManager
from creme_core.forms.fields import CremeEntityField
from creme_core.forms.widgets import ListViewWidget, DependentSelect

from products.models import Product, Service, Category, SubCategory, ServiceCategory

from billing.models import ProductLine, ServiceLine
from billing.constants import DEFAULT_VAT

from creme import form_post_save

default_decimal = Decimal()

class LineCreateForm(CremeModelForm):
    document_id = IntegerField(widget=HiddenInput()) #TODO: it's possible to hack the form: document_id different from the one given is the url

    def save(self):
        instance = self.instance
        created = False if instance.pk else True
        instance.document_id = self.cleaned_data['document_id']
        instance.is_paid = False
        super(LineCreateForm, self).save()
        
        form_post_save.send (sender=self.instance.__class__, instance=self.instance, created=created)

bm = FieldBlockManager(('general', _(u'Informations sur la ligne'), ['related_item', 'comment', 'quantity', 'unit_price',
                                                                     'discount', 'credit', 'total_discount', 'vat', 'user'])
     )


class ProductLineCreateForm(LineCreateForm):
    related_item = CremeEntityField(label=_("Produit"), model=Product, widget=ListViewWidget(attrs={'selection_cb':'creme.product_line.auto_populate_selection','selection_cb_args':{'attr':'name','values':['unit_price']}}))

    blocks = bm

    class Meta:
        model = ProductLine
        exclude = ('on_the_fly_item', 'document', 'is_paid')


class ProductLineOnTheFlyCreateForm(LineCreateForm):
    blocks = FieldBlockManager(
        ('general', _(u'Informations sur la ligne'), ['on_the_fly_item', 'comment', 'quantity', 'unit_price',
                                                                     'discount', 'credit', 'total_discount', 'vat', 'user']),
        ('additionnal', _(u'Fonctionnalités supplémentaires'), ['has_to_register_as','category','sub_category'])
     )

    has_to_register_as = BooleanField(label=_(u"Enregistrer en tant que produit ?"), required=False,
                                      help_text=_(u"Ceci vous permer d'enregistrer un produit à la volée en tant que produit à par entière, dans ce cas là, la catégorie et sous-catégorie est obligatoire."))
    category           = ModelChoiceField(queryset=Category.objects.all(), label=_(u'Catégorie'),
                                          widget=DependentSelect(target_id='id_sub_category', target_url='/products/sub_category/load'),
                                          required=False)
    sub_category       = ModelChoiceField(queryset=SubCategory.objects.all(),
                                          label=_(u'Sous-catégorie'),
                                          widget=Select(attrs={'id': 'id_sub_category'}),
                                          required=False)

    class Meta:
        model = ProductLine
        exclude = ('related_item', 'document', 'is_paid')

    def __init__(self, *args, **kwargs):
        super(ProductLineOnTheFlyCreateForm, self).__init__(*args, **kwargs)
        if self.instance.pk is not None:
            self.blocks = FieldBlockManager(('general', _(u'Informations sur la ligne'), ['on_the_fly_item', 'comment', 'quantity', 'unit_price',
                                                                     'discount', 'credit', 'total_discount', 'vat', 'user']),)

    def clean(self):
        cleaned_data = self.cleaned_data

        has_to_register_as = cleaned_data.get('has_to_register_as')
        category           = cleaned_data.get('category')
        sub_category       = cleaned_data.get('sub_category')

        if has_to_register_as and category is None:
            raise ValidationError(_(u'Catégorie obligatoire si vous souhaitez enregistrer en tant que produit.'))
        if has_to_register_as and category and sub_category is None:
            raise ValidationError(_(u'Sous-catégorie obligatoire si vous souhaitez enregistrer en tant que produit.'))
        return cleaned_data

    def save(self):
        cleaned_data = self.cleaned_data
        
        if cleaned_data.get('has_to_register_as'):
            p = Product()
            p.name = cleaned_data.get('on_the_fly_item', '')
            p.user = cleaned_data.get('user')
            p.code = 0
            p.unit_price = cleaned_data.get('unit_price', 0)
            p.category = cleaned_data.get('category', 0)
            p.sub_category = cleaned_data.get('sub_category', 0)
            p.save()
            
            plcf = ProductLineCreateForm({
                    'document_id':    cleaned_data.get('document_id'),
                    'related_item':   '%s,' % p.pk,
                    'quantity':       cleaned_data.get('quantity', 0),
                    'unit_price':     cleaned_data.get('unit_price', default_decimal),
                    'credit':         cleaned_data.get('credit', default_decimal),
                    'discount':       cleaned_data.get('discount', default_decimal),
                    'total_discount': cleaned_data.get('total_discount', False),
                    'vat':            cleaned_data.get('vat', DEFAULT_VAT),
                    'user':           p.user.pk,
                    'comment':        cleaned_data.get('comment', '')
                   })

            if plcf.is_valid():
                plcf.save()
        else:
            super(ProductLineOnTheFlyCreateForm, self).save()


class ServiceLineCreateForm(LineCreateForm):
    related_item = CremeEntityField(label=_("Service"), model=Service, widget=ListViewWidget(attrs={'selection_cb':'creme.product_line.auto_populate_selection','selection_cb_args':{'attr':'name','values':['unit_price']}}))
    #selection_cb uses the same callback than ProductLineCreateForm so is there no Product line block on the Service line block page => Error. Implements its onw function when it'll be necessary

    blocks = bm

    class Meta:
        model = ServiceLine
        exclude = ('on_the_fly_item', 'document', 'is_paid')


class ServiceLineOnTheFlyCreateForm(LineCreateForm):
    class Meta:
        model = ServiceLine
        exclude = ('related_item', 'document', 'is_paid')
        
    blocks = FieldBlockManager(
        ('general', _(u'Informations sur la ligne'), ['on_the_fly_item', 'comment', 'quantity', 'unit_price',
                                                                     'discount', 'credit', 'total_discount', 'vat', 'user']),
        ('additionnal', _(u'Fonctionnalités supplémentaires'), ['has_to_register_as','category'])
     )

    has_to_register_as = BooleanField(label=_(u"Enregistrer en tant que service ?"), required=False,
                                      help_text=_(u"Ceci vous permer d'enregistrer un service à la volée en tant que service à par entière."))

    category           = ModelChoiceField(queryset=ServiceCategory.objects.all(), label=_(u'Catégorie de service'),
                                          required=False)

    def __init__(self, *args, **kwargs):
        super(ServiceLineOnTheFlyCreateForm, self).__init__(*args, **kwargs)
        if self.instance.pk is not None:
            self.blocks = FieldBlockManager(('general', _(u'Informations sur la ligne'), ['on_the_fly_item', 'comment', 'quantity', 'unit_price',
                                                                     'discount', 'credit', 'total_discount', 'vat', 'user']),)

    def clean(self):
        cleaned_data = self.cleaned_data

        has_to_register_as = cleaned_data.get('has_to_register_as')
        category           = cleaned_data.get('category')

        if has_to_register_as and category is None:
            raise ValidationError(_(u'Catégorie obligatoire si vous souhaitez enregistrer en tant que service.'))
        return cleaned_data

    def save(self):
        cleaned_data = self.cleaned_data

        if cleaned_data.get('has_to_register_as'):
            s = Service()
            s.name = cleaned_data.get('on_the_fly_item', '')
            s.user = cleaned_data.get('user')
            s.reference = ''
            s.category = cleaned_data.get('category')
            s.unit_price = cleaned_data.get('unit_price', 0)
            s.save()

            slcf = ServiceLineCreateForm({
                    'document_id':    cleaned_data.get('document_id'),
                    'related_item':   '%s,' % s.pk,
                    'quantity':       cleaned_data.get('quantity', 0),
                    'unit_price':     cleaned_data.get('unit_price', default_decimal),
                    'credit':         cleaned_data.get('credit', default_decimal),
                    'discount':       cleaned_data.get('discount', default_decimal),
                    'total_discount': cleaned_data.get('total_discount', False),
                    'vat':            cleaned_data.get('vat', DEFAULT_VAT),
                    'user':           s.user.pk,
                    'comment':        cleaned_data.get('comment', '')
                   })

            if slcf.is_valid():
                slcf.save()
        else:
            super(ServiceLineOnTheFlyCreateForm, self).save()

