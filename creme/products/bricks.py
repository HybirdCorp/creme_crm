################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2014-2025  Hybird
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

from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from creme import products
from creme.creme_core.gui.bricks import SimpleBrick

Product = products.get_product_model()
Service = products.get_service_model()


class ImagesBrick(SimpleBrick):
    id = SimpleBrick.generate_id('products', 'images')
    verbose_name = _('Images of product/service')
    # dependencies  = (Document,) ??
    template_name = 'products/bricks/images.html'
    target_ctypes = (Product, Service)
    permissions = 'products'

    def get_template_context(self, context, **extra_kwargs):
        entity = context['object']

        return super().get_template_context(
            context,
            add_images_url=(
                reverse('products__add_images_to_product', args=(entity.id,))
                if isinstance(entity, Product) else
                reverse('products__add_images_to_service', args=(entity.id,))
            ),
            **extra_kwargs
        )
