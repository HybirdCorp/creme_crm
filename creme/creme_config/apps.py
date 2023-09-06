################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2023  Hybird
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
from django.utils.translation import ngettext

from creme.creme_core.apps import CremeAppConfig


class CremeConfigConfig(CremeAppConfig):
    default = True
    name = 'creme.creme_config'
    verbose_name = _('General configuration')
    dependencies = ['creme.creme_core']
    credentials = CremeAppConfig.CRED_REGULAR

    def all_apps_ready(self):
        super().all_apps_ready()

        self.hook_password_validators()

        from .registry import config_registry
        self.populate_config_registry(config_registry)

    # TODO: define our own classes?
    def hook_password_validators(self):
        from django.contrib.auth import password_validation

        # ---
        def minlen_get_help_text(this):
            return ngettext(
                'The password must contain at least %(min_length)d character.',
                'The password must contain at least %(min_length)d characters.',
                this.min_length,
            ) % {'min_length': this.min_length}

        password_validation.MinimumLengthValidator.get_help_text = minlen_get_help_text

        # ---
        def personal_get_help_text(self):
            return _(
                "The password can’t be too similar to the other personal information."
            )

        password_validation.UserAttributeSimilarityValidator.get_help_text = personal_get_help_text

        # ---
        def common_get_help_text(self):
            return _("The password can’t be a commonly used password.")

        password_validation.CommonPasswordValidator.get_help_text = common_get_help_text

        # ---
        def numeric_get_help_text(self):
            return _("The password can’t be entirely numeric.")

        password_validation.NumericPasswordValidator.get_help_text = numeric_get_help_text

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
            bricks.WorldSettingsBrick,
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
