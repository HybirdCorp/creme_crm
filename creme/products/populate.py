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

from products.models import Product, Service, Category, SubCategory


class Populator(BasePopulator):
    dependencies = ['creme_core']

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

        jewelry = create(Category, 1, name=_(u"Jewelry"))
        create(SubCategory, 1, name=_(u"Ring"),     category=jewelry)
        create(SubCategory, 2, name=_(u"Bracelet"), category=jewelry)
        create(SubCategory, 3, name=_(u"Necklace"), category=jewelry)
        create(SubCategory, 4, name=_(u"Earrings"), category=jewelry)

        mobile = create(Category, 2, name=_(u"Mobile"))
        create(SubCategory, 5, name=_(u"Iphone"),     category=mobile)
        create(SubCategory, 6, name=_(u"Blackberry"), category=mobile)
        create(SubCategory, 7, name=_(u"Samsung"),    category=mobile)
        create(SubCategory, 8, name=_(u"Android"),    category=mobile)

        informatic = create(Category, 3, name=_(u"Informatic"))
        create(SubCategory, 9, name=_(u"Laptops"),   category=informatic)
        create(SubCategory, 10, name=_(u"Desktops"), category=informatic)
        create(SubCategory, 11, name=_(u"Tablet"),   category=informatic)
        create(SubCategory, 12, name=_(u"Notebook"), category=informatic)

        travels = create(Category, 4, name=_(u"Travels"))
        create(SubCategory, 13, name=_(u"Fly"),      category=travels)
        create(SubCategory, 14, name=_(u"Hotel"),    category=travels)
        create(SubCategory, 15, name=_(u"Week-end"), category=travels)
        create(SubCategory, 16, name=_(u"Rent"),     category=travels)

        vehicle = create(Category, 5, name=_(u"Vehicle"))
        create(SubCategory, 17, name=_(u"Car"),   category=vehicle)
        create(SubCategory, 18, name=_(u"Moto"),  category=vehicle)
        create(SubCategory, 19, name=_(u"Boat"),  category=vehicle)
        create(SubCategory, 20, name=_(u"Plane"), category=vehicle)

        games_toys = create(Category, 6, name=_(u"Games & Toys"))
        create(SubCategory, 21, name=_(u"Boys"),    category=games_toys)
        create(SubCategory, 22, name=_(u"Girls"),   category=games_toys)
        create(SubCategory, 23, name=_(u"Teens"),   category=games_toys)
        create(SubCategory, 24, name=_(u"Baybies"), category=games_toys)

        clothes = create(Category, 7, name=_(u"Clothes"))
        create(SubCategory, 25, name=_(u"Men"),     category=clothes)
        create(SubCategory, 26, name=_(u"Women"),   category=clothes)
        create(SubCategory, 27, name=_(u"Kids"),    category=clothes)
        create(SubCategory, 28, name=_(u"Baybies"), category=clothes)

        SearchConfigItem.create(Product, ['name', 'description', 'category__name', 'sub_category__name'])
        SearchConfigItem.create(Service, ['name', 'description', 'category__name', 'sub_category__name'])
