################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2026  Hybird
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

from typing import override

from django.utils.translation import gettext_lazy as _

from creme.creme_config.apps import CremeConfigConfigMixin
from creme.creme_core.apps import CremeAppConfig


class MobileConfig(CremeConfigConfigMixin, CremeAppConfig):
    default = True
    name = 'creme.mobile'
    verbose_name = _('Mobile')
    dependencies = ['creme.persons', 'creme.activities']
    credentials = CremeAppConfig.CRED_NONE

    @override
    def register_bricks(self, brick_registry):
        from . import bricks

        brick_registry.register(
            brick_registry.Tag.DETAIL,
            bricks.FavoritePersonsBrick,
        )

    @override
    def register_creme_config(self, config_registry):
        from creme.activities import constants as act_constants
        from creme.activities import models as act_models

        act_app_config = config_registry.get_app_registry('activities')
        act_app_config.get_model_conf(
            act_models.Status
        ).disablor.register_needed_instances(
            'mobile',
            act_constants.UUID_STATUS_IN_PROGRESS,
            act_constants.UUID_STATUS_DONE,
        )
        act_app_config.get_model_conf(
            act_models.ActivityType
        ).disablor.register_needed_instances(
            'mobile',
            act_constants.UUID_TYPE_PHONECALL,
        )
        act_app_config.get_model_conf(
            act_models.ActivitySubType
        ).disablor.register_needed_instances(
            'mobile',
            act_constants.UUID_SUBTYPE_PHONECALL_OUTGOING,
            act_constants.UUID_SUBTYPE_PHONECALL_FAILED,
        )

    @override
    def register_setting_keys(self, setting_key_registry):
        from . import setting_keys

        setting_key_registry.register(
            setting_keys.location_map_url_key,
        )
