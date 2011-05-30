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

from creme_core.models import SearchConfigItem
from creme_core.models.header_filter import HeaderFilterItem, HeaderFilter, HFI_FIELD
from creme_core.utils import create_or_update as create
from creme_core.management.commands.creme_populate import BasePopulator

from products.models import Product, Service, Category, SubCategory


class Populator(BasePopulator):
    dependencies = ['creme.creme_core']

    def populate(self, *args, **kwargs):
        hf   = HeaderFilter.create(pk='products-hf_product', name=_(u'Product view'), model=Product)
        pref = 'products-hfi_product_'
        create(HeaderFilterItem, pref + 'images', order=1, name='images__name',   title=_(u'Images - Name'),   type=HFI_FIELD, header_filter=hf, has_a_filter=True, editable=False, sortable=False, filter_string="images__name__icontains")
        create(HeaderFilterItem, pref + 'name',   order=2, name='name',           title=_(u'Name'),            type=HFI_FIELD, header_filter=hf, has_a_filter=True, editable=True,  sortable=True,  filter_string="name__icontains")
        create(HeaderFilterItem, pref + 'code',   order=3, name='code',           title=_(u'Code'),            type=HFI_FIELD, header_filter=hf, has_a_filter=True, editable=True,  sortable=True,  filter_string="code__icontains")
        create(HeaderFilterItem, pref + 'user',   order=4, name='user__username', title=_(u'User - Username'), type=HFI_FIELD, header_filter=hf, has_a_filter=True, editable=True,  sortable=True,  filter_string="user__username__icontains")

        hf   = HeaderFilter.create(pk='products-hf_service', name=_(u'Service view'), model=Service)
        pref = 'products-hfi_service_'
        create(HeaderFilterItem, pref + 'images', order=1, name='images__name',   title=_(u'Images - Name'),   type=HFI_FIELD, header_filter=hf, has_a_filter=True, editable=False, sortable=False, filter_string="images__name__icontains")
        create(HeaderFilterItem, pref + 'name',   order=2, name='name',           title=_(u'Name'),            type=HFI_FIELD, header_filter=hf, has_a_filter=True, editable=True,  sortable=True,  filter_string="name__icontains")
        create(HeaderFilterItem, pref + 'ref',    order=3, name='reference',      title=_(u'Reference'),       type=HFI_FIELD, header_filter=hf, has_a_filter=True, editable=True,  sortable=True,  filter_string="reference__icontains")
        create(HeaderFilterItem, pref + 'user',   order=4, name='user__username', title=_(u'User - Username'), type=HFI_FIELD, header_filter=hf, has_a_filter=True, editable=True,  sortable=True,  filter_string="user__username__icontains")

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
        SearchConfigItem.create(Service, ['name', 'description', 'category__name', 'sub_category__name'])
