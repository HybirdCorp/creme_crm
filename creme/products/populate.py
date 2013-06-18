# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2013  Hybird
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

from creme.creme_core.models import SearchConfigItem, HeaderFilterItem, HeaderFilter
from creme.creme_core.management.commands.creme_populate import BasePopulator

from .models import Product, Service, Category, SubCategory


class Populator(BasePopulator):
    dependencies = ['creme_core']

    def populate(self):
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

        if not Category.objects.exists():
            create_cat = Category.objects.create
            create_subcat = SubCategory.objects.create

            jewelry = create_cat(name=_(u"Jewelry"))
            create_subcat(name=_(u"Ring"),     category=jewelry)
            create_subcat(name=_(u"Bracelet"), category=jewelry)
            create_subcat(name=_(u"Necklace"), category=jewelry)
            create_subcat(name=_(u"Earrings"), category=jewelry)

            mobile = create_cat(name=_(u"Mobile"))
            create_subcat(name=_(u"Iphone"),     category=mobile)
            create_subcat(name=_(u"Blackberry"), category=mobile)
            create_subcat(name=_(u"Samsung"),    category=mobile)
            create_subcat(name=_(u"Android"),    category=mobile)

            informatic = create_cat(name=_(u"Informatic"))
            create_subcat(name=_(u"Laptops"),   category=informatic)
            create_subcat(name=_(u"Desktops"), category=informatic)
            create_subcat(name=_(u"Tablet"),   category=informatic)
            create_subcat(name=_(u"Notebook"), category=informatic)

            travels = create_cat(name=_(u"Travels"))
            create_subcat(name=_(u"Fly"),      category=travels)
            create_subcat(name=_(u"Hotel"),    category=travels)
            create_subcat(name=_(u"Week-end"), category=travels)
            create_subcat(name=_(u"Rent"),     category=travels)

            vehicle = create_cat(name=_(u"Vehicle"))
            create_subcat(name=_(u"Car"),   category=vehicle)
            create_subcat(name=_(u"Moto"),  category=vehicle)
            create_subcat(name=_(u"Boat"),  category=vehicle)
            create_subcat(name=_(u"Plane"), category=vehicle)

            games_toys = create_cat(name=_(u"Games & Toys"))
            create_subcat(name=_(u"Boys"),    category=games_toys)
            create_subcat(name=_(u"Girls"),   category=games_toys)
            create_subcat(name=_(u"Teens"),   category=games_toys)
            create_subcat(name=_(u"Baybies"), category=games_toys)

            clothes = create_cat(name=_(u"Clothes"))
            create_subcat(name=_(u"Men"),     category=clothes)
            create_subcat(name=_(u"Women"),   category=clothes)
            create_subcat(name=_(u"Kids"),    category=clothes)
            create_subcat(name=_(u"Baybies"), category=clothes)

        SearchConfigItem.create_if_needed(Product, ['name', 'description', 'category__name', 'sub_category__name'])
        SearchConfigItem.create_if_needed(Service, ['name', 'description', 'category__name', 'sub_category__name'])
