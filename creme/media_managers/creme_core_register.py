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

from django.utils.translation import ugettext_lazy as _

from creme.creme_core.registry import creme_registry
from creme.creme_core.gui import creme_menu, block_registry, icon_registry, bulk_update_registry

from .models import Image
from .blocks import ImageBlock, last_images_block, image_view_block


creme_registry.register_app('media_managers', _(u'Media managers'), '/media')
creme_registry.register_entity_models(Image)

reg_item = creme_menu.register_app('media_managers', '/media_managers/').register_item
reg_item('/media_managers/',          _(u'Portal of media managers'), 'media_managers')
reg_item('/media_managers/image/add', Image.creation_label,           'media_managers.add_image')
reg_item('/media_managers/images',    _(u'All images'),               'media_managers')

block_registry.register_4_model(Image, ImageBlock())
block_registry.register(last_images_block, image_view_block)

icon_registry.register(Image, 'images/image_%(size)s.png')

bulk_update_registry.register(
    (Image, ['image']),
)
