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

from logging import info

from django.utils.translation import ugettext as _
from django.conf import settings

from creme_core.models import SearchConfigItem, HeaderFilterItem, HeaderFilter, BlockDetailviewLocation, BlockPortalLocation
from creme_core.blocks import properties_block, relations_block, customfields_block, history_block
from creme_core.utils import create_if_needed
from creme_core.management.commands.creme_populate import BasePopulator

from media_managers.models import MediaCategory, Image
from media_managers.blocks import *


class Populator(BasePopulator):
    dependencies = ['creme_core']

    def populate(self, *args, **kwargs):
        #TODO: created by 'products' & 'persons' app ?? (pk_string)
        create_if_needed(MediaCategory, {'pk': 1}, name=_(u"Product image"),      is_custom=False)
        create_if_needed(MediaCategory, {'pk': 2}, name=_(u"Organisation logo"),  is_custom=False)
        create_if_needed(MediaCategory, {'pk': 3}, name=_(u"Contact photograph"), is_custom=False)

        hf = HeaderFilter.create(pk='media_managers-hf_image', name=_(u'Image view'), model=Image)
        hf.set_items([HeaderFilterItem.build_4_field(model=Image, name='name'),
                      HeaderFilterItem.build_4_field(model=Image, name='image'),
                      HeaderFilterItem.build_4_field(model=Image, name='description'),
                      HeaderFilterItem.build_4_field(model=Image, name='user__username'),
                      HeaderFilterItem.build_4_field(model=Image, name='categories'),
                     ])

        BlockDetailviewLocation.create(block_id=image_view_block.id_,   order=40,  zone=BlockDetailviewLocation.LEFT,   model=Image)
        BlockDetailviewLocation.create_4_model_block(order=5, zone=BlockDetailviewLocation.RIGHT, model=Image)
        BlockDetailviewLocation.create(block_id=customfields_block.id_, order=40,  zone=BlockDetailviewLocation.RIGHT,  model=Image)
        BlockDetailviewLocation.create(block_id=history_block.id_,      order=100, zone=BlockDetailviewLocation.RIGHT,  model=Image)
        BlockDetailviewLocation.create(block_id=properties_block.id_,   order=450, zone=BlockDetailviewLocation.RIGHT,  model=Image)
        BlockDetailviewLocation.create(block_id=relations_block.id_,    order=500, zone=BlockDetailviewLocation.RIGHT,  model=Image)

        BlockPortalLocation.create(app_name='media_managers', block_id=last_images_block.id_, order=10)
        BlockPortalLocation.create(app_name='media_managers', block_id=history_block.id_,     order=30)

        if 'assistants' in settings.INSTALLED_APPS:
            info('Assistants app is installed => we use the assistants blocks on detail view')

            from assistants.blocks import alerts_block, memos_block, todos_block, messages_block

            BlockDetailviewLocation.create(block_id=todos_block.id_,    order=600, zone=BlockDetailviewLocation.RIGHT, model=Image)
            BlockDetailviewLocation.create(block_id=memos_block.id_,    order=700, zone=BlockDetailviewLocation.RIGHT, model=Image)
            BlockDetailviewLocation.create(block_id=alerts_block.id_,   order=800, zone=BlockDetailviewLocation.RIGHT, model=Image)
            BlockDetailviewLocation.create(block_id=messages_block.id_, order=900, zone=BlockDetailviewLocation.RIGHT, model=Image)

            BlockPortalLocation.create(app_name='media_managers', block_id=memos_block.id_,    order=100)
            BlockPortalLocation.create(app_name='media_managers', block_id=alerts_block.id_,   order=200)
            BlockPortalLocation.create(app_name='media_managers', block_id=messages_block.id_, order=400)

        SearchConfigItem.create_if_needed(Image, ['name', 'description', 'categories__name'])
