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

from creme_core.models import SearchConfigItem, HeaderFilterItem, HeaderFilter, BlockDetailviewLocation
from creme_core.blocks import properties_block, relations_block, customfields_block, history_block
from creme_core.utils import create_or_update as create
from creme_core.management.commands.creme_populate import BasePopulator

from media_managers.models import MediaCategory, Image


class Populator(BasePopulator):
    dependencies = ['creme.creme_core']

    def populate(self, *args, **kwargs):
        #TODO: created by 'products' & 'persons' app ?? (pk_string)
        create(MediaCategory, pk=1, name=_(u"Product image"),      is_custom=False)
        create(MediaCategory, pk=2, name=_(u"Organisation logo"),  is_custom=False)
        create(MediaCategory, pk=3, name=_(u"Contact photograph"), is_custom=False)

        hf = HeaderFilter.create(pk='media_managers-hf_image', name=_(u'Image view'), model=Image)
        hf.set_items([HeaderFilterItem.build_4_field(model=Image, name='name'),
                      HeaderFilterItem.build_4_field(model=Image, name='image'),
                      HeaderFilterItem.build_4_field(model=Image, name='description'),
                      HeaderFilterItem.build_4_field(model=Image, name='user__username'),
                      HeaderFilterItem.build_4_field(model=Image, name='categories'),
                     ])

        BlockDetailviewLocation.create(block_id=customfields_block.id_,  order=40,  zone=BlockDetailviewLocation.RIGHT,  model=Image)
        BlockDetailviewLocation.create(block_id=history_block.id_,       order=100, zone=BlockDetailviewLocation.RIGHT,  model=Image)
        BlockDetailviewLocation.create(block_id=properties_block.id_,    order=450, zone=BlockDetailviewLocation.RIGHT,  model=Image)
        BlockDetailviewLocation.create(block_id=relations_block.id_,     order=500, zone=BlockDetailviewLocation.RIGHT,  model=Image)

        SearchConfigItem.create(Image, ['name', 'description', 'categories__name'])

