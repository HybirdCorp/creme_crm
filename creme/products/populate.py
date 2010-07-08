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

from creme_core.models import SearchConfigItem, SearchField
from creme_core.models.header_filter import HeaderFilterItem, HeaderFilter, HFI_FIELD
from creme_core.utils import create_or_update_models_instance as create
from creme_core.utils.meta import get_verbose_field_name
from creme_core.management.commands.creme_populate import BasePopulator

from products.models import Product, Service, ServiceCategory, Category, SubCategory


class Populator(BasePopulator):
    dependencies = ['creme.core']

    def populate(self, *args, **kwargs):
        get_ct = ContentType.objects.get_for_model

        hf_id = create(HeaderFilter, 'products-hf_product', name=u'Vue de Produit', entity_type_id=get_ct(Product).id, is_custom=False).id
        pref = 'products-hfi_product_'
        create(HeaderFilterItem, pref + 'images', order=1, name='images', title=_(u'Images'),      type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=False, sortable=False, filter_string="images__name__icontains")
        create(HeaderFilterItem, pref + 'name',   order=2, name='name',   title=_(u'Nom'),         type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True,  sortable=True,  filter_string="name__icontains")
        create(HeaderFilterItem, pref + 'code',   order=3, name='code',   title=_(u'Code'),        type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True,  sortable=True,  filter_string="code__icontains")
        create(HeaderFilterItem, pref + 'user',   order=4, name='user',   title=_(u'Utilisateur'), type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True,  sortable=True,  filter_string="user__username__icontains")

        hf_id = create(HeaderFilter, 'products-hf_service', name='Vue de Service', entity_type_id=get_ct(Service).id, is_custom=False).id
        pref  = 'products-hfi_service_'
        create(HeaderFilterItem, pref + 'images', order=1, name='images',    title=_(u'Images'),      type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=False, sortable=False, filter_string="images__name__icontains")
        create(HeaderFilterItem, pref + 'name',   order=2, name='name',      title=_(u'Nom'),         type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True,  sortable=True,  filter_string="name__icontains")
        create(HeaderFilterItem, pref + 'ref',    order=3, name='reference', title=_(u'Référence'),   type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True,  sortable=True,  filter_string="reference__icontains")
        create(HeaderFilterItem, pref + 'user',   order=4, name='user',      title=_(u'Utilisateur'), type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True, editable=True,  sortable=True,  filter_string="user__username__icontains")


        #TODO: move to client's populate.py ??
        create(ServiceCategory, 1, name=_(u"Catégorie 1"), description=_(u"Description catégorie 1"))
        create(ServiceCategory, 2, name=_(u"Catégorie 2"), description=_(u"Description catégorie 2"))

        cooking             = create(Category, 1, name=_(u"Cuisine"),      description=_(u"Articles pour la cuisine"))
        fruits_n_vegetables = create(Category, 2, name=_(u"Primeurs"),     description=_(u"Fruits, légumes, ..."))
        computer            = create(Category, 3, name=_(u"Informatique"), description=_(u"La gamme des geeks"))

        create(SubCategory, 1, name=_(u"Four à vide"), description=_(u"Four à vide"),                         category_id=cooking.pk)
        create(SubCategory, 2, name=_(u"Casseroles"),  description=_(u"Pour faire la cuisine"),               category_id=cooking.pk)
        create(SubCategory, 3, name=_(u"Portables"),   description=_(u"Les PC portables"),                    category_id=computer.pk)
        create(SubCategory, 4, name=_(u"Bureau"),      description=_(u"les PC de salon"),                     category_id=computer.pk)
        create(SubCategory, 5, name=_(u"Accessoires"), description=_(u"Accessoires pour PC fixes/portables"), category_id=computer.pk)
        create(SubCategory, 6, name=_(u"Fruits"),      description=_(u"Des fruits: bananes, ..."),            category_id=fruits_n_vegetables.pk)
        create(SubCategory, 7, name=_(u"Légumes"),     description=_(u"Des légumes : carottes, ..."),         category_id=fruits_n_vegetables.pk)

        model = Product
        sci = create(SearchConfigItem, content_type_id=ContentType.objects.get_for_model(model).id)
        SCI_pk = sci.pk
        sci_fields = ['name', 'description', 'category__name', 'sub_category__name']
        for i, field in enumerate(sci_fields):
            create(SearchField, field=field, field_verbose_name=get_verbose_field_name(model, field), order=i, search_config_item_id=SCI_pk)

        model = Service
        sci = create(SearchConfigItem, content_type_id=ContentType.objects.get_for_model(model).id)
        SCI_pk = sci.pk
        sci_fields = ['name', 'description', 'category__name']
        for i, field in enumerate(sci_fields):
            create(SearchField, field=field, field_verbose_name=get_verbose_field_name(model, field), order=i, search_config_item_id=SCI_pk)