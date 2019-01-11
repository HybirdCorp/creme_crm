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


class VCFsConfig(CremeAppConfig):
    name = 'creme.vcfs'
    verbose_name = _('Vcfs')
    dependencies = ['creme.persons']
    credentials = CremeAppConfig.CRED_NONE

    def register_actions(self, actions_registry):
        from . import actions

        actions_registry.register_instance_actions(
            actions.GenerateVcfAction,
        )

    def register_buttons(self, button_registry):
        from . import buttons

        button_registry.register(buttons.GenerateVcfButton)

    def register_menu(self, creme_menu):
        from django.urls import reverse_lazy as reverse

        from creme.creme_core.auth import build_creation_perm

        from creme.persons import get_contact_model

        creme_menu.get('features', 'persons-directory') \
                  .add(creme_menu.URLItem('vcfs-import', url=reverse('vcfs__import'),
                                          label=_('Import from a VCF file'),
                                          perm=build_creation_perm(get_contact_model()),
                                         ),
                       priority=200,
                      )
