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

from media_managers.models import MediaCategory, Image


class Populator(BasePopulator):
    dependencies = ['creme.core']

    def populate(self, *args, **kwargs):
        #TODO: created by 'products' & 'persons' app ?? (pk_string)
        create(MediaCategory, name=_(u"Product image"),      is_custom=False)
        create(MediaCategory, name=_(u"Organisation logo"),  is_custom=False)
        create(MediaCategory, name=_(u"Contact photograph"), is_custom=False)

        hf_id = create(HeaderFilter, 'media_managers-hf_image', name=_(u"Image view"), entity_type_id=ContentType.objects.get_for_model(Image).id, is_custom=False).id
        pref  = 'media_managers-hfi_image_'
        create(HeaderFilterItem, pref + 'name',  order=1, name='name',        title=_(u'Name'),         type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True,  editable=True, filter_string="name__icontains" )
        create(HeaderFilterItem, pref + 'image', order=2, name='image',       title=_(u'Image'),       type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=False, editable=False)
        create(HeaderFilterItem, pref + 'descr', order=3, name='description', title=_(u'Description'), type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True,  editable=True, filter_string="description__icontains")
        create(HeaderFilterItem, pref + 'user',  order=4, name='user',        title=_(u'User'),        type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=True,  editable=True, filter_string="user__username__icontains" )
        create(HeaderFilterItem, pref + 'cat',   order=5, name='categories',  title=_(u'Categories'),  type=HFI_FIELD, header_filter_id=hf_id, has_a_filter=False, editable=False)

        model = Image
        sci = create(SearchConfigItem, content_type_id=ContentType.objects.get_for_model(model).id)
        SCI_pk = sci.pk
        #m2m fields excluded for the moment see creme_config/forms/search.py
        sci_fields = ['name', 'description']#, 'categories__name']
        for i, field in enumerate(sci_fields):
            create(SearchField, field=field, field_verbose_name=get_verbose_field_name(model, field), order=i, search_config_item_id=SCI_pk)
