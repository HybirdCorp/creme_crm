# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2021  Hybird
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

from django.utils.translation import gettext_lazy as _

from creme.creme_core.apps import CremeAppConfig


class CremeConfigConfig(CremeAppConfig):
    default = True
    name = 'creme.creme_config'
    verbose_name = _('General configuration')
    dependencies = ['creme.creme_core']
    credentials = CremeAppConfig.CRED_REGULAR

    def all_apps_ready(self):
        super().all_apps_ready()

        from .registry import config_registry
        self.populate_config_registry(config_registry)

    def populate_config_registry(self, config_registry):
        from creme.creme_core.apps import creme_app_configs

        for app_config in creme_app_configs():
            config_registry.get_app_registry(app_config.label, create=True)

            register_creme_config = getattr(app_config, 'register_creme_config', None)

            if register_creme_config is not None:
                register_creme_config(config_registry)

    def register_creme_config(self, config_registry):
        from . import bricks

        config_registry.register_portal_bricks(bricks.ExportButtonBrick)

    def register_bricks(self, brick_registry):
        from . import bricks

        brick_registry.register(
            bricks.SettingsBrick,
            bricks.PropertyTypesBrick,
            bricks.RelationTypesBrick,
            bricks.CustomRelationTypesBrick,
            bricks.SemiFixedRelationTypesBrick,
            bricks.CustomFieldsBrick,
            bricks.CustomEnumsBrick,
            bricks.CustomFormsBrick,
            bricks.BrickDetailviewLocationsBrick,
            bricks.BrickHomeLocationsBrick,
            bricks.BrickDefaultMypageLocationsBrick,
            bricks.BrickMypageLocationsBrick,
            bricks.RelationBricksConfigBrick,
            bricks.InstanceBricksConfigBrick,
            bricks.ExportButtonBrick,
            bricks.FieldsConfigsBrick,
            bricks.CustomBricksConfigBrick,
            bricks.MenuBrick,
            bricks.ButtonMenuBrick,
            bricks.UsersBrick,
            bricks.TeamsBrick,
            bricks.SearchConfigBrick,
            bricks.HistoryConfigBrick,
            bricks.UserRolesBrick,
            bricks.UserSettingValuesBrick,
            bricks.EntityFiltersBrick,
            bricks.HeaderFiltersBrick,
        )

    # def register_menu(self, creme_menu):
    #     from django.urls import reverse_lazy as reverse
    #
    #     from creme.creme_core import models as core_models
    #
    #     from . import gui
    #
    #     URLItem = creme_menu.URLItem
    #     creme_menu.get(
    #         'creme', 'user',
    #     ).add(
    #         gui.TimezoneItem('creme_config-timezone'),
    #         priority=5,
    #     ).add(
    #         URLItem(
    #             'my_settings', label=_('My settings'),
    #             url=reverse('creme_config__user_settings'),
    #         ),
    #         priority=30,
    #     )
    #     creme_menu.get(
    #         'features',
    #     ).add(
    #         gui.ConfigContainerItem(
    #             'creme_config',
    #         ).add(
    #             URLItem(
    #                 'creme_config-portal', url=reverse('creme_config__portal'),
    #                 label=_('General configuration'), perm='creme_config',
    #             ),
    #             priority=10,
    #         ).add(
    #             gui.CurrentAppConfigItem('creme_config-current_app'),
    #             priority=13,
    #         ).add(
    #             creme_menu.ItemGroup(
    #                 'creme_config-portals',
    #             ).add(
    #                 URLItem(
    #                     'creme_config-blocks', url=reverse('creme_config__bricks'),
    #                     label=_('Blocks'), perm='creme_config',
    #                 ),
    #                 priority=10,
    #             ).add(
    #                 URLItem(
    #                     'creme_config-custom_fields',
    #                     url=reverse('creme_config__custom_fields'),
    #                     label=core_models.CustomField._meta.verbose_name_plural,
    #                     perm='creme_config',
    #                 ),
    #                 priority=20,
    #             ).add(
    #                 URLItem(
    #                     'creme_config-fields', url=reverse('creme_config__fields'),
    #                     label=_('Fields'), perm='creme_config',
    #                 ),
    #                 priority=30,
    #             ).add(
    #                 URLItem(
    #                     'creme_config-custom_forms',
    #                     url=reverse('creme_config__custom_forms'),
    #                     label=_('Custom forms'),
    #                     perm='creme_config',
    #                 ),
    #                 priority=20,
    #             ).add(
    #                 URLItem(
    #                     'creme_config-history', url=reverse('creme_config__history'),
    #                     label=_('History'), perm='creme_config',
    #                 ),
    #                 priority=40,
    #             ).add(
    #                 URLItem(
    #                     'creme_config-button_menu', url=reverse('creme_config__buttons'),
    #                     label=_('Button menu'), perm='creme_config',
    #                 ),
    #                 priority=50,
    #             ).add(
    #                 URLItem(
    #                     'creme_config-search', url=reverse('creme_config__search'),
    #                     label=_('Search'), perm='creme_config',
    #                 ),
    #                 priority=70,
    #             ).add(
    #                 URLItem(
    #                     'creme_config-roles', url=reverse('creme_config__roles'),
    #                     label=_('Roles and credentials'), perm='creme_config',
    #                 ),
    #                 priority=80,
    #             ).add(
    #                 URLItem(
    #                     'creme_config-property_types', url=reverse('creme_config__ptypes'),
    #                     label=core_models.CremePropertyType._meta.verbose_name_plural,
    #                     perm='creme_config',
    #                 ),
    #                 priority=90,
    #             ).add(
    #                 URLItem(
    #                     'creme_config-relation_types', url=reverse('creme_config__rtypes'),
    #                     label=core_models.RelationType._meta.verbose_name_plural,
    #                     perm='creme_config',
    #                 ),
    #                 priority=100,
    #             ).add(
    #                 URLItem(
    #                     'creme_config-users', url=reverse('creme_config__users'),
    #                     label=_('Users'), perm='creme_config',
    #                 ),
    #                 priority=110,
    #             ),
    #             priority=20
    #         ),
    #         priority=10000,
    #     )

    def register_menu_entries(self, menu_registry):
        from creme.creme_core import menu as core_menu

        from . import menu

        menu_registry.register(menu.CremeConfigEntry)

        # Hook CremeEntry
        children = core_menu.CremeEntry.child_classes
        children.insert(
            children.index(core_menu.MyPageEntry),
            menu.TimezoneEntry,
        )
        children.insert(
            children.index(core_menu.MyJobsEntry) + 1,
            menu.MySettingsEntry,
        )
