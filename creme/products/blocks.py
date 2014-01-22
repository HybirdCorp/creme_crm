# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2014  Hybird
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

from creme.creme_core.gui.block import Block

from .models import Product, Service


class ImagesBlock(Block):
    id_           = Block.generate_id('products', 'images')
    #dependencies  = (Image,) ??
    template_name = 'products/block_images.html'
    target_ctypes = (Product, Service)

    def detailview_display(self, context):
        entity = context['object']
        return self._render(self.get_block_template_context(context,
                                                            update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, entity.pk),
                                                            object_type=entity.__class__.__name__.lower(), #'product' or 'service', used by URL
                                                           )
                           )


images_block = ImagesBlock()
