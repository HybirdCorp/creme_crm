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


class RecurrentsConfig(CremeAppConfig):
    name = 'creme.recurrents'
    verbose_name = _(u'Recurrent documents')
    dependencies = ['creme.creme_core']

    def all_apps_ready(self):
        from . import get_rgenerator_model

        self.RecurrentGenerator = get_rgenerator_model()

        super(RecurrentsConfig, self).all_apps_ready()

    def register_entity_models(self, creme_registry):
        creme_registry.register_entity_models(self.RecurrentGenerator)

    def register_bulk_update(self, bulk_update_registry):
        # TODO: use a custom form that allows the edition when last_generation is None
        bulk_update_registry.register(self.RecurrentGenerator, exclude=['first_generation'])

    def register_icons(self, icon_registry):
        icon_registry.register(self.RecurrentGenerator, 'images/recurrent_doc_%(size)s.png')

    def register_menu(self, creme_menu):
        # from django.conf import settings

        RGenerator = self.RecurrentGenerator

        # if settings.OLD_MENU:
        #     from django.urls import reverse_lazy as reverse
        #     from creme.creme_core.auth import build_creation_perm
        #
        #     reg_item = creme_menu.register_app('recurrents', '/recurrents/').register_item
        #     reg_item(reverse('recurrents__portal'),           _(u'Portal of recurrent documents'), 'recurrents')
        #     reg_item(reverse('recurrents__list_generators'),  _(u'All recurrent generators'),      'recurrents')
        #     reg_item(reverse('recurrents__create_generator'), RGenerator.creation_label,           build_creation_perm(RGenerator))
        # else:
        creme_menu.get('features', 'management') \
                  .add(creme_menu.URLItem.list_view('recurrents-generators', model=RGenerator), priority=100)
        creme_menu.get('creation', 'any_forms') \
                  .get_or_create_group('management', _(u'Management'), priority=50) \
                  .add_link('recurrents-create_rgenerator', RGenerator, priority=100)
