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

from creme_core.models import EntityCredentials
from creme_core.gui.block import Block, SimpleBlock, list4url

from media_managers.models import Image


class ImageBlock(SimpleBlock):
    template_name = 'media_managers/templatetags/block_image.html'


class ImageViewBlock(SimpleBlock):
    id_           = Block.generate_id('media_managers', 'image_view')
    dependencies  = (Image,)
    verbose_name  = _(u"Image view")
    template_name = 'media_managers/templatetags/block_image_view.html'
    target_ctypes = (Image,)


#TODO: transform to a paginated block with all allowed images ??
class LastImagesBlock(Block):
    id_           = Block.generate_id('media_managers', 'last_images')
    dependencies  = (Image,)
    verbose_name  = _(u"Last added images")
    template_name = 'media_managers/templatetags/block_last_images.html'
    target_apps   = ('media_managers',)

    def portal_display(self, context, ct_ids):
        images = EntityCredentials.filter(context['user'],
                                          Image.objects.filter(is_deleted=False).order_by('created'),
                                         )[:5] #TODO: make '5' configurable
        return self._render(self.get_block_template_context(context,
                                                            update_url='/creme_core/blocks/reload/portal/%s/%s/' % (self.id_, list4url(ct_ids)),
                                                            objects_list=images,
                                                           ))


image_view_block  = ImageViewBlock()
last_images_block = LastImagesBlock()
