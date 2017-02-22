# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2016  Hybird
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

# NB: This app will be removed in Creme 1.8

# from django.conf import settings
from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _

# from creme.creme_core.apps import CremeAppConfig

# from .models import Image


# class MediaManagersConfig(CremeAppConfig):
class MediaManagersConfig(AppConfig):
    name = 'creme.media_managers'
    verbose_name = _(u'Media managers')
    # dependencies = ['creme.creme_core']

    # def register_creme_app(self, creme_registry):
    #     creme_registry.register_app('media_managers', _(u'Media managers'), '/media')
    #
    # def register_entity_models(self, creme_registry):
    #     creme_registry.register_entity_models(Image)
    #
    # def register_blocks(self, block_registry):
    #     from .blocks import ImageBlock, last_images_block, image_view_block
    #
    #     block_registry.register_4_model(Image, ImageBlock())
    #     block_registry.register(last_images_block, image_view_block)
    #
    # def register_bulk_update(self, bulk_update_registry):
    #     bulk_update_registry.register(Image, exclude=['image'])
    #
    # def register_field_printers(self, field_printers_registry):
    #     from creme.creme_core.gui.field_printers import print_foreignkey_html, print_many2many_html
    #
    #     def print_fk_image_html(entity, fval, user, field):
    #         return u'''<a onclick="creme.dialogs.image('%s').open();"%s>%s</a>''' % (
    #                 fval.get_image_url(),
    #                 ' class="is_deleted"' if fval.is_deleted else u'',
    #                 fval.get_entity_summary(user)
    #             ) if user.has_perm_to_view(fval) else settings.HIDDEN_VALUE
    #
    #     def print_image_summary_html(instance, related_entity, fval, user, field):
    #         return u'''<a onclick="creme.dialogs.image('%s').open();"%s>%s</a>''' % (
    #                     instance.get_image_url(),
    #                     ' class="is_deleted"' if instance.is_deleted else u'',
    #                     instance.get_entity_summary(user),
    #                 ) if user.has_perm_to_view(instance) else settings.HIDDEN_VALUE
    #
    #     print_foreignkey_html.register(Image, print_fk_image_html)
    #     print_many2many_html.register(Image,
    #                                   printer=print_image_summary_html,
    #                                   enumerator=print_many2many_html.enumerator_entity,
    #                                  )
    #
    # def register_icons(self, icon_registry):
    #     icon_registry.register(Image, 'images/image_%(size)s.png')
    #
    # def register_menu(self, creme_menu):
    #    if settings.OLD_MENU:
    #        reg_item = creme_menu.register_app('media_managers', '/media_managers/').register_item
    #        reg_item('/media_managers/',          _(u'Portal of media managers'), 'media_managers')
    #        reg_item('/media_managers/image/add', Image.creation_label,           'media_managers.add_image')
    #        reg_item('/media_managers/images',    _(u'All images'),               'media_managers')
    #    else:
    #        pass
    #
    # def register_quickforms(self, quickforms_registry):
    #     from .forms.quick import ImageQuickForm
    #
    #     quickforms_registry.register(Image, ImageQuickForm)
