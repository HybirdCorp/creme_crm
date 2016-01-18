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

from django.core.urlresolvers import reverse
from django.db.models import (CharField, IntegerField, DecimalField, ForeignKey,
        ManyToManyField, PROTECT)
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.models import CremeEntity

from creme.media_managers.models import Image

from .other_models import Category, SubCategory


class AbstractProduct(CremeEntity):
    name              = CharField(_(u'Name'), max_length=100)
    code              = IntegerField(_(u'Code'), default=0)
    description       = CharField(_(u'Description'), max_length=200)
    unit_price        = DecimalField(_(u'Unit price'), max_digits=8, decimal_places=2)
    unit              = CharField(_(u'Unit'), max_length=100, blank=True).set_tags(optional=True)
    quantity_per_unit = IntegerField(_(u'Quantity/Unit'), blank=True, null=True) \
                                    .set_tags(optional=True)
    weight            = DecimalField(_(u'Weight'), max_digits=8, decimal_places=2,
                                     blank=True, null=True,
                                    ).set_tags(optional=True)
    stock             = IntegerField(_(u'Quantity/Stock'), blank=True, null=True) \
                                    .set_tags(optional=True)
    web_site          = CharField(_(u'Web Site'), max_length=100,
                                  blank=True, null=True,
                                 ).set_tags(optional=True)
    category          = ForeignKey(Category, verbose_name=_(u'Category'), on_delete=PROTECT)
    sub_category      = ForeignKey(SubCategory, verbose_name=_(u'Sub-category'),
                                   on_delete=PROTECT,
                                  )
    images            = ManyToManyField(Image, blank=True,
                                        verbose_name=_(u'Images'),
                                        related_name='ProductImages_set',
                                       )

    creation_label = _('Add a product')

    class Meta:
        abstract = True
        app_label    = 'products'
        verbose_name = _(u'Product')
        verbose_name_plural = _(u'Products')
        ordering = ('name',)

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('products__view_product', args=(self.id,))

    @staticmethod
    def get_create_absolute_url():
        return reverse('products__create_product')

    def get_edit_absolute_url(self):
        return reverse('products__edit_product', args=(self.id,))

    @staticmethod
    def get_lv_absolute_url():
        return reverse('products__list_products')


class Product(AbstractProduct):
    class Meta(AbstractProduct.Meta):
        swappable = 'PRODUCTS_PRODUCT_MODEL'
