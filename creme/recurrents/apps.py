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


class RecurrentsConfig(CremeAppConfig):
    default = True
    name = 'creme.recurrents'
    verbose_name = _('Recurrent documents')
    dependencies = ['creme.creme_core']

    def all_apps_ready(self):
        from . import get_rgenerator_model

        self.RecurrentGenerator = get_rgenerator_model()

        super().all_apps_ready()

    def register_entity_models(self, creme_registry):
        creme_registry.register_entity_models(self.RecurrentGenerator)

    def register_bulk_update(self, bulk_update_registry):
        # TODO: use a custom form that allows the edition when last_generation is None
        bulk_update_registry.register(
            self.RecurrentGenerator, exclude=['first_generation'],
        )

    def register_custom_forms(self, cform_registry):
        from . import custom_forms

        cform_registry.register(
            custom_forms.GENERATOR_CREATION_CFORM,
            custom_forms.GENERATOR_EDITION_CFORM,
        )

    def register_fields_config(self, fields_config_registry):
        fields_config_registry.register_models(self.RecurrentGenerator)

    def register_icons(self, icon_registry):
        icon_registry.register(
            self.RecurrentGenerator, 'images/recurrent_doc_%(size)s.png',
        )

    # def register_menu(self, creme_menu):
    #     RGenerator = self.RecurrentGenerator
    #     creme_menu.get(
    #         'features'
    #     ).get_or_create(
    #         creme_menu.ContainerItem, 'management', priority=50,
    #         defaults={'label': _('Management')},
    #     ).add(
    #         creme_menu.URLItem.list_view('recurrents-generators', model=RGenerator),
    #         priority=100,
    #     )
    #     creme_menu.get(
    #         'creation', 'any_forms'
    #     ).get_or_create_group(
    #         'management', _('Management'), priority=50,
    #     ).add_link('recurrents-create_rgenerator', RGenerator, priority=100)

    def register_menu_entries(self, menu_registry):
        from . import menu

        menu_registry.register(
            menu.RecurrentGeneratorsEntry,
            menu.RecurrentGeneratorCreationEntry,
        )

    def register_creation_menu(self, creation_menu_registry):
        creation_menu_registry.get_or_create_group(
            'management', _('Management'), priority=50,
        ).add_link(
            'recurrents-create_rgenerator', self.RecurrentGenerator, priority=100,
        )
