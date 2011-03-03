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

from creme_core.models import SearchConfigItem
from creme_core.models.header_filter import HeaderFilterItem, HeaderFilter, HFI_FIELD
from creme_core.utils import create_or_update as create
from creme_core.management.commands.creme_populate import BasePopulator

from media_managers.models import MediaCategory, Image


class Populator(BasePopulator):
    dependencies = ['creme.creme_core']

    def populate(self, *args, **kwargs):
        #TODO: created by 'products' & 'persons' app ?? (pk_string)
        create(MediaCategory, name=_(u"Product image"),      is_custom=False)
        create(MediaCategory, name=_(u"Organisation logo"),  is_custom=False)
        create(MediaCategory, name=_(u"Contact photograph"), is_custom=False)

        hf = HeaderFilter.create(pk='media_managers-hf_image', name=_(u'Image view'), model=Image)
        pref  = 'media_managers-hfi_image_'
        create(HeaderFilterItem, pref + 'name',  order=1, name='name',           title=_(u'Name'),            type=HFI_FIELD, header_filter=hf, has_a_filter=True,  editable=True, filter_string="name__icontains" )
        create(HeaderFilterItem, pref + 'image', order=2, name='image',          title=_(u'Image'),           type=HFI_FIELD, header_filter=hf, has_a_filter=False, editable=False)
        create(HeaderFilterItem, pref + 'descr', order=3, name='description',    title=_(u'Description'),     type=HFI_FIELD, header_filter=hf, has_a_filter=True,  editable=True, filter_string="description__icontains")
        create(HeaderFilterItem, pref + 'user',  order=4, name='user__username', title=_(u'User - Username'), type=HFI_FIELD, header_filter=hf, has_a_filter=True,  editable=True, filter_string="user__username__icontains" )
        create(HeaderFilterItem, pref + 'cat',   order=5, name='categories',     title=_(u'Categories'),      type=HFI_FIELD, header_filter=hf, has_a_filter=False, editable=False)

        SearchConfigItem.create(Image, ['name', 'description', 'categories__name'])

