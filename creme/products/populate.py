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

from django.utils.translation import ugettext as _

from creme_core.models import SearchConfigItem, HeaderFilterItem, HeaderFilter
from creme_core.utils import create_or_update as create
from creme_core.management.commands.creme_populate import BasePopulator

from products.models import Product, Service, ServiceCategory, Category, SubCategory


class Populator(BasePopulator):
    dependencies = ['creme.creme_core']

    def populate(self, *args, **kwargs):
        hf = HeaderFilter.create(pk='products-hf_product', name=_(u'Product view'), model=Product)
        hf.set_items([HeaderFilterItem.build_4_field(model=Product, name='images__name'),
                      HeaderFilterItem.build_4_field(model=Product, name='name'),
                      HeaderFilterItem.build_4_field(model=Product, name='code'),
                      HeaderFilterItem.build_4_field(model=Product, name='user__username'),
                     ])

        hf = HeaderFilter.create(pk='products-hf_service', name=_(u'Service view'), model=Service)
        hf.set_items([HeaderFilterItem.build_4_field(model=Service, name='images__name'),
                      HeaderFilterItem.build_4_field(model=Service, name='name'),
                      HeaderFilterItem.build_4_field(model=Service, name='reference'),
                      HeaderFilterItem.build_4_field(model=Service, name='user__username'),
                     ])

        #TODO: move to customer's populate.py ??
        create(ServiceCategory, 1, name=_(u"Category 1"), description=_(u"Description of 'category 1'"))
        create(ServiceCategory, 2, name=_(u"Category 2"), description=_(u"Description of 'category 2'"))

        cooking             = create(Category, 1, name=_(u"Cooking"),          description=_(u"Items for the kitchen"))
        fruits_n_vegetables = create(Category, 2, name=_(u"Fruit/vegetables"), description=_(u"Early fruit and vegetables"))
        computer            = create(Category, 3, name=_(u"Informatic"),       description=_(u"Geeks' sideline"))

        create(SubCategory, 1, name=_(u"Oven"),        description=_(u"Gas oven"),                         category=cooking)
        create(SubCategory, 2, name=_(u"Pans"),        description=_(u"To cook"),                          category=cooking)
        create(SubCategory, 3, name=_(u"Laptops"),     description=_(u"Laptops, netbooks"),                category=computer)
        create(SubCategory, 4, name=_(u"Desktops"),    description=_(u"Home computers"),                   category=computer)
        create(SubCategory, 5, name=_(u"Accessories"), description=_(u"Accessories for desktops/laptops"), category=computer)
        create(SubCategory, 6, name=_(u"Fruits"),      description=_(u"Bananas, apples..."),               category=fruits_n_vegetables)
        create(SubCategory, 7, name=_(u"Vegetables"),  description=_(u"Carrots, potatoes..."),             category=fruits_n_vegetables)

        SearchConfigItem.create(Product, ['name', 'description', 'category__name', 'sub_category__name'])
        SearchConfigItem.create(Service, ['name', 'description', 'category__name'])
