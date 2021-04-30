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


class CrudityConfig(CremeAppConfig):
    default = True
    name = 'creme.crudity'
    verbose_name = _('External data management')
    dependencies = ['creme.creme_core']

    def ready(self):
        super().ready()

        from . import signals  # NOQA

    # def register_menu(self, creme_menu):
    #     from django.urls import reverse_lazy as reverse
    #
    #     URLItem = creme_menu.URLItem
    #     creme_menu.get('features', 'tools') \
    #               .get_or_create(creme_menu.ItemGroup, 'crudity', priority=250,
    #                              defaults={'label': _('External data')},
    #                             ) \
    #               .add(URLItem('crudity-waiting_actions', url=reverse('crudity__actions'),
    #                            label=_('Waiting actions'), perm='crudity',
    #                           ),
    #                    priority=10,
    #                   ) \
    #               .add(URLItem('crudity-history', reverse('crudity__history'),
    #                            label=_('History'), perm='crudity',
    #                           ),
    #                    priority=20,
    #                   )

    def register_menu_entries(self, menu_registry):
        from . import menu

        menu_registry.register(
            menu.WaitingActionsEntry,
            menu.CrudityHistoryEntry,
        )

    def register_setting_keys(self, setting_key_registry):
        from . import setting_keys

        setting_key_registry.register(setting_keys.sandbox_key)
