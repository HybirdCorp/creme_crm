# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015  Hybird
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

from creme.creme_core.apps import CremeAppConfig

from .models import Image


class MediaManagersConfig(CremeAppConfig):
    name = 'creme.media_managers'
    verbose_name = _(u'Media managers')
    dependencies = ['creme.creme_core']

    def register_creme_app(self, creme_registry):
        creme_registry.register_app('media_managers', _(u'Media managers'), '/media')

    def register_entity_models(self, creme_registry):
        creme_registry.register_entity_models(Image)

    def register_blocks(self, block_registry):
        from .blocks import ImageBlock, last_images_block, image_view_block

        block_registry.register_4_model(Image, ImageBlock())
        block_registry.register(last_images_block, image_view_block)

    def register_bulk_update(self, bulk_update_registry):
        bulk_update_registry.register(Image, exclude=['image'])

    def register_icons(self, icon_registry):
        icon_registry.register(Image, 'images/image_%(size)s.png')

    def register_menu(self, creme_menu):
        reg_item = creme_menu.register_app('media_managers', '/media_managers/').register_item
        reg_item('/media_managers/',          _(u'Portal of media managers'), 'media_managers')
        reg_item('/media_managers/image/add', Image.creation_label,           'media_managers.add_image')
        reg_item('/media_managers/images',    _(u'All images'),               'media_managers')

    def register_quickforms(self, quickforms_registry):
        from .forms.quick import ImageQuickForm

        quickforms_registry.register(Image, ImageQuickForm)
