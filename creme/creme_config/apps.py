################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2025  Hybird
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
        config_registry.register_user_bricks(
            bricks.BrickMypageLocationsBrick,
            bricks.NotificationChannelConfigItemsBrick,
            bricks.UserSettingValuesBrick,
        )

    def register_permissions(self, special_perm_registry):
        from . import auth

        special_perm_registry.register(
            auth.user_config_perm,
            auth.role_config_perm,
        )

    def register_bricks(self, brick_registry):
        from . import bricks

        brick_registry.register(
            bricks.WorldSettingsBrick,
            bricks.SettingsBrick,
            bricks.PropertyTypesBrick,
            bricks.RelationTypesBrick,
            bricks.CustomRelationTypesBrick,
            bricks.SemiFixedRelationTypesBrick,
            bricks.CustomEntitiesBrick,
            bricks.CustomFieldsBrick,
            bricks.CustomEnumsBrick,
            bricks.CustomFormsBrick,
            bricks.WorkflowsBrick,
            bricks.BrickDetailviewLocationsBrick,
            bricks.BrickHomeLocationsBrick,
            bricks.BrickDefaultMypageLocationsBrick,
            bricks.RelationBricksConfigBrick,
            bricks.InstanceBricksConfigBrick,
            bricks.FieldsConfigsBrick,
            bricks.CustomBricksConfigBrick,
            bricks.MenuBrick,
            bricks.NotificationChannelsBrick,
            bricks.ButtonMenuBrick,
            bricks.UsersBrick,
            bricks.TeamsBrick,
            bricks.SearchConfigBrick,
            bricks.HistoryConfigBrick,
            bricks.UserRolesBrick,
            bricks.EntityFiltersBrick,
            bricks.HeaderFiltersBrick,
            bricks.FileRefsBrick,
        )

    def register_menu_entries(self, menu_registry):
        import creme.creme_core.menu as core_menu

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

    def register_notification(self, notification_registry):
        from . import notification

        notification_registry.register_content(
            content_cls=notification.PasswordChangeContent,
        ).register_content(
            content_cls=notification.RoleSwitchContent,
        )
