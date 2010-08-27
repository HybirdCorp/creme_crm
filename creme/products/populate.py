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

from django.utils.translation import ugettext as _
from django.contrib.contenttypes.models import ContentType

from creme_core.models import SearchConfigItem
from creme_core.models.header_filter import HeaderFilterItem, HeaderFilter, HFI_FIELD
from creme_core.utils import create_or_update_models_instance as create
from creme_core.management.commands.creme_populate import BasePopulator

from products.models import Product, Service, ServiceCategory, Category, SubCategory


class Populator(BasePopulator):
    dependencies = ['creme.core']

    def populate(self, *args, **kwargs):
        get_ct = ContentType.objects.get_for_model

        hf_id = create(HeaderFilter, 'products-hf_product', name=_(u'Product view'), entity_type_id=get_ct(Product).id, is_custom=False).id
        pref = 'products-hfi_product_'
        create(HeaderFilterItem, pref + 'images', order=1, name='images', title=_(u'Images'), type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=False, sortable=False, filter_string="images__name__icontains")
        create(HeaderFilterItem, pref + 'name',   order=2, name='name',   title=_(u'Name'),   type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True,  sortable=True,  filter_string="name__icontains")
        create(HeaderFilterItem, pref + 'code',   order=3, name='code',   title=_(u'Code'),   type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True,  sortable=True,  filter_string="code__icontains")
        create(HeaderFilterItem, pref + 'user',   order=4, name='user',   title=_(u'User'),   type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True,  sortable=True,  filter_string="user__username__icontains")

        hf_id = create(HeaderFilter, 'products-hf_service', name=_(u'Service view'), entity_type_id=get_ct(Service).id, is_custom=False).id
        pref  = 'products-hfi_service_'
        create(HeaderFilterItem, pref + 'images', order=1, name='images',    title=_(u'Images'),    type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=False, sortable=False, filter_string="images__name__icontains")
        create(HeaderFilterItem, pref + 'name',   order=2, name='name',      title=_(u'Name'),      type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True,  sortable=True,  filter_string="name__icontains")
        create(HeaderFilterItem, pref + 'ref',    order=3, name='reference', title=_(u'Reference'), type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True,  sortable=True,  filter_string="reference__icontains")
        create(HeaderFilterItem, pref + 'user',   order=4, name='user',      title=_(u'User'),      type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True,  sortable=True,  filter_string="user__username__icontains")


        #TODO: move to client's populate.py ??
        create(ServiceCategory, 1, name=_(u"Category 1"), description=_(u"Description of 'category 1'"))
        create(ServiceCategory, 2, name=_(u"Category 2"), description=_(u"Description of 'category 2'"))

        cooking             = create(Category, 1, name=_(u"Cooking"),          description=_(u"Items for the kitchen"))
        fruits_n_vegetables = create(Category, 2, name=_(u"Fruit/vegetables"), description=_(u"Early fruit and vegetables"))
        computer            = create(Category, 3, name=_(u"Informatic"),       description=_(u"Geeks' sideline"))

        create(SubCategory, 1, name=_(u"Oven"),        description=_(u"Gas oven"),                         category_id=cooking.pk)
        create(SubCategory, 2, name=_(u"Pans"),        description=_(u"To cook"),                          category_id=cooking.pk)
        create(SubCategory, 3, name=_(u"Laptops"),     description=_(u"Laptops, netbooks"),                category_id=computer.pk)
        create(SubCategory, 4, name=_(u"Desktops"),    description=_(u"Home computers"),                   category_id=computer.pk)
        create(SubCategory, 5, name=_(u"Accessories"), description=_(u"Accessories for desktops/laptops"), category_id=computer.pk)
        create(SubCategory, 6, name=_(u"Fruits"),      description=_(u"Bananas, apples..."),               category_id=fruits_n_vegetables.pk)
        create(SubCategory, 7, name=_(u"Vegetables"),  description=_(u"Carrots, potatoes..."),             category_id=fruits_n_vegetables.pk)

        SearchConfigItem.create(Product, ['name', 'description', 'category__name', 'sub_category__name'])
        SearchConfigItem.create(Service, ['name', 'description', 'category__name'])
