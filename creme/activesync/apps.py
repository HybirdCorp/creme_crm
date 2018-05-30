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

from django.core import checks
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.apps import CremeAppConfig
from creme.creme_core.checks import Tags


class ActivesyncConfig(CremeAppConfig):
    name = 'creme.activesync'
    verbose_name = _(u'Mobile synchronization')
    dependencies = ['creme.persons', 'creme.activities']

    def ready(self):
        def deprecate(**kwargs):
            return [checks.Warning('The app "activesync" is deprecated.',
                                   hint='It will probably be removed in the next release if nobody works on it.',
                                   obj='activesync',
                                   id='creme.activesync.E001',
                                  ),
                   ]

        checks.register(Tags.settings)(deprecate)

    def all_apps_ready(self):
        super(ActivesyncConfig, self).all_apps_ready()

        from . import signals

    def register_bricks(self, brick_registry):
        from . import bricks

        brick_registry.register(bricks.UserMobileSyncConfigBrick,
                                bricks.MobileSyncConfigBrick,
                               )

    def register_menu(self, creme_menu):
        # from django.conf import settings
        from django.urls import reverse_lazy as reverse

        # if settings.OLD_MENU:
        #     reg_item = creme_menu.get_app_item('persons').register_item
        #     reg_item(reverse('activesync__sync'), _(u'Contact synchronisation'), 'persons')
        # else:
        creme_menu.get('features', 'persons-directory') \
                  .add(creme_menu.URLItem('activesync-sync',
                                          url=reverse('activesync__sync'),
                                          label=_(u'Contact synchronisation'),
                                          perm='persons',
                                         ),
                       priority=1000
                      )

    def register_setting_keys(self, setting_key_registry):
        from .setting_keys import skeys

        setting_key_registry.register(*skeys)

    def register_user_setting_keys(self, user_setting_key_registry):
        from .setting_keys import user_skeys

        user_setting_key_registry.register(*user_skeys)
