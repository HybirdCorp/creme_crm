# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2018  Hybird
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
    verbose_name = _('General configuration')
    dependencies = ['creme.creme_core']
    credentials = CremeAppConfig.CRED_REGULAR

    def register_bricks(self, brick_registry):
        from . import bricks

        brick_registry.register(
            bricks.SettingsBrick,
            bricks.PropertyTypesBrick,
            bricks.RelationTypesBrick,
            bricks.CustomRelationTypesBrick,
            bricks.SemiFixedRelationTypesBrick,
            bricks.CustomFieldsBrick,
            bricks.BrickDetailviewLocationsBrick,
            bricks.BrickHomeLocationsBrick,
            bricks.BrickDefaultMypageLocationsBrick,
            bricks.BrickMypageLocationsBrick,
            bricks.RelationBricksConfigBrick,
            bricks.InstanceBricksConfigBrick,
            bricks.FieldsConfigsBrick,
            bricks.CustomBricksConfigBrick,
            bricks.ButtonMenuBrick,
            bricks.UsersBrick,
            bricks.TeamsBrick,
            bricks.SearchConfigBrick,
            bricks.HistoryConfigBrick,
            bricks.UserRolesBrick,
            bricks.UserSettingValuesBrick,
        )

    def register_menu(self, creme_menu):
        from django.urls import reverse_lazy as reverse

        from creme.creme_core import models as core_models

        from .gui import TimezoneItem, ConfigContainerItem

        URLItem = creme_menu.URLItem
        creme_menu.get('creme', 'user') \
                  .add(TimezoneItem('creme_config-timezone'), priority=5) \
                  .add(URLItem('my_settings', url=reverse('creme_config__user_settings'), label=_('My settings')),
                       priority=30,
                      )
        creme_menu.get('features') \
                  .add(ConfigContainerItem('creme_config')
                           .add(URLItem('creme_config-portal', url=reverse('creme_config__portal'),
                                        label=_('General configuration'), perm='creme_config',
                                       ),
                                priority=10
                               )
                           .add(creme_menu.ItemGroup('creme_config-portals')
                                   .add(URLItem('creme_config-blocks', url=reverse('creme_config__bricks'),
                                                label=_('Blocks'), perm='creme_config',
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
                                                label=_('Fields'), perm='creme_config',
                                               ),
                                        priority=30
                                       )
                                   .add(URLItem('creme_config-history', url=reverse('creme_config__history'),
                                                label=_('History'), perm='creme_config',
                                               ),
                                        priority=40
                                       )
                                   .add(URLItem('creme_config-button_menu', url=reverse('creme_config__buttons'),
                                                label=_('Button menu'), perm='creme_config',
                                               ),
                                        priority=50
                                       )
                                   .add(URLItem('creme_config-search', url=reverse('creme_config__search'),
                                                label=_('Search'), perm='creme_config',
                                               ),
                                        priority=70
                                       )
                                   .add(URLItem('creme_config-roles', url=reverse('creme_config__roles'),
                                                label=_('Roles and credentials'), perm='creme_config',
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
                                                label=_('Users'), perm='creme_config',
                                               ),
                                        priority=110
                                       ),
                                priority=20
                               ),
                       priority=10000,
                      )
