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

from django.utils.translation import ugettext_lazy as _

from creme.creme_core.apps import CremeAppConfig


class CremeConfigConfig(CremeAppConfig):
    name = 'creme.creme_config'
    verbose_name = _(u'General configuration')
    dependencies = ['creme.creme_core']
    credentials = CremeAppConfig.CRED_REGULAR

    # def register_creme_app(self, creme_registry):
    #     creme_registry.register_app('creme_config', _(u'General configuration'),
    #                                 '/creme_config',
    #                                 credentials=creme_registry.CRED_REGULAR,
    #                                )

    def register_blocks(self, block_registry):
        from .blocks import blocks_list

        block_registry.register(*blocks_list)

    def register_menu(self, creme_menu):
        from django.conf import settings
        from django.core.urlresolvers import reverse_lazy as reverse

        if settings.OLD_MENU:
            reg_item = creme_menu.register_app('creme_config', '/creme_config/').register_item
            # TODO: 'creme_config'-> '' (perm is not really 'creme_config', but this item is not visible if the user has not 'creme_config' perm)
            reg_item(reverse('creme_config__portal'),              _(u'Portal of general configuration'), 'creme_config')
            reg_item(reverse('creme_config__rtypes'),              _(u'Relation types settings'),         'creme_config')
            reg_item(reverse('creme_config__ptypes'),              _(u'Property types settings'),         'creme_config')
            reg_item(reverse('creme_config__fields'),              _(u'Fields settings'),                 'creme_config')
            reg_item(reverse('creme_config__custom_fields'),       _(u'Custom fields settings'),          'creme_config')
            reg_item(reverse('creme_config__blocks'),              _(u'Blocks settings'),                 'creme_config')
            reg_item(reverse('creme_config__edit_preferred_menu'), _(u'Default preferred menu settings'), 'creme_core.can_admin') # TODO: viewer mode if user has credentials 'creme_core' ?
            reg_item(reverse('creme_config__buttons'),             _(u'Button menu settings'),            'creme_config')
            reg_item(reverse('creme_config__search'),              _(u'Search settings'),                 'creme_config')
            reg_item(reverse('creme_config__history'),             _(u'History settings'),                'creme_config')
            reg_item(reverse('creme_config__users'),               _(u'Users settings'),                  'creme_config')
            reg_item(reverse('creme_config__roles'),               _(u'Roles and credentials settings'),  'creme_config')
        else:
            from creme.creme_core import models as core_models

            from .gui import TimezoneItem, ConfigContainerItem

            URLItem = creme_menu.URLItem
            creme_menu.get('creme', 'user') \
                      .add(TimezoneItem('creme_config-timezone'), priority=5) \
                      .add(URLItem('my_settings', url=reverse('creme_config__user_settings'), label=_(u'My settings')),
                           priority=20
                          )
            creme_menu.get('features') \
                      .add(ConfigContainerItem('creme_config')
                               .add(URLItem('creme_config-portal', url=reverse('creme_config__portal'),
                                            label=_(u'General configuration'), perm='creme_config',
                                           ),
                                    priority=10
                                   )
                               .add(creme_menu.ItemGroup('creme_config-portals')
                                       .add(URLItem('creme_config-blocks', url=reverse('creme_config__blocks'),
                                                    label=_(u'Blocks'), perm='creme_config',
                                                   ),
                                            priority=10
                                           )
                                       .add(URLItem('creme_config-custom_fields',
                                                    url=reverse('creme_config__custom_fields'),
                                                    label=core_models.CustomField._meta.verbose_name_plural,
                                                    perm='creme_config',
                                                   ),
                                            priority=20
                                           )
                                       .add(URLItem('creme_config-fields', url=reverse('creme_config__fields'),
                                                    label=_(u'Fields'), perm='creme_config',
                                                   ),
                                            priority=30
                                           )
                                       .add(URLItem('creme_config-history', url=reverse('creme_config__history'),
                                                    label=_(u'History'), perm='creme_config',
                                                   ),
                                            priority=40
                                           )
                                       .add(URLItem('creme_config-button_menu', url=reverse('creme_config__buttons'),
                                                    label=_(u'Button menu'), perm='creme_config',
                                                   ),
                                            priority=50
                                           )
                                       .add(URLItem('creme_config-search', url=reverse('creme_config__search'),
                                                    label=_(u'Search'), perm='creme_config',
                                                   ),
                                            priority=70
                                           )
                                       .add(URLItem('creme_config-roles', url=reverse('creme_config__roles'),
                                                    label=_(u'Roles and credentials'), perm='creme_config',
                                                   ),
                                            priority=80
                                           )
                                       .add(URLItem('creme_config-property_types', url=reverse('creme_config__ptypes'),
                                                    label=core_models.CremePropertyType._meta.verbose_name_plural,
                                                    perm='creme_config',
                                                   ),
                                            priority=90
                                           )
                                       .add(URLItem('creme_config-relation_types', url=reverse('creme_config__rtypes'),
                                                    label=core_models.RelationType._meta.verbose_name_plural,
                                                    perm='creme_config',
                                                   ),
                                            priority=100
                                           )
                                       .add(URLItem('creme_config-users', url=reverse('creme_config__users'),
                                                    label=_(u'Users'), perm='creme_config',
                                                   ),
                                            priority=110
                                           ),
                                    priority=20
                                   ),
                           priority=10000,
                          )

    # def register_setting_key(self, setting_key_registry):
    #     from .setting_keys import theme_key, timezone_key
    #
    #     setting_key_registry.register(theme_key, timezone_key)
