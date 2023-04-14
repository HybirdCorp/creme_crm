################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2022-2023  Hybird
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

from django.db import models
from django.utils.translation import gettext_lazy as _

from ..global_info import cached_per_request
from .base import CremeModel
from .manager import CremeEntityManager


class WorldSettingsManager(CremeEntityManager):
    @cached_per_request('creme_core-world_settings')
    def instance(self):
        instance = self.first()
        if instance is None:
            raise RuntimeError(
                'No instance of WorldSettings has been found ; '
                'have you run the command "creme_populate"?'
            )

        return instance


class AbstractActivityWorldSettings(CremeModel):
    menu_icon = models.ImageField(
        verbose_name=_('Menu icon'), upload_to='creme_core', blank=True,
    )
    password_change_enabled = models.BooleanField(
        verbose_name=_('Allow all users to change their own password?'),
        default=True,
    )
    password_reset_enabled = models.BooleanField(
        verbose_name=_('Enable the «Lost password» feature?'),
        default=True,
        help_text=_(
            'This feature allows users to reset their password if they forgot '
            'it. The login page proposes to receive an email to start the '
            'reset process.'
        ),
    )
    user_name_change_enabled = models.BooleanField(
        verbose_name=_('Can users change their own displayed name?'),
        default=True,
    )

    objects = WorldSettingsManager()

    class Meta:
        app_label = 'creme_core'
        abstract = True


class WorldSettings(AbstractActivityWorldSettings):
    class Meta(AbstractActivityWorldSettings.Meta):
        swappable = 'CREME_CORE_WSETTINGS_MODEL'
