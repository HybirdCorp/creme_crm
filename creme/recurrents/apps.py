# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015  Hybird
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

#    def ready(self):
    def all_apps_ready(self):
        from . import get_rgenerator_model

        self.RecurrentGenerator = get_rgenerator_model()

#        super(RecurrentsConfig, self).ready()
        super(RecurrentsConfig, self).all_apps_ready()

    def register_creme_app(self, creme_registry):
        creme_registry.register_app('recurrents', _(u'Recurrent documents'), '/recurrents')

    def register_entity_models(self, creme_registry):
        creme_registry.register_entity_models(self.RecurrentGenerator)

    def register_bulk_update(self, bulk_update_registry):
        # TODO: use a custom form that allows the edition when last_generation is None
        bulk_update_registry.register(self.RecurrentGenerator, exclude=['first_generation'])

    def register_icons(self, icon_registry):
        icon_registry.register(self.RecurrentGenerator, 'images/recurrent_doc_%(size)s.png')

    def register_menu(self, creme_menu):
        from django.core.urlresolvers import reverse_lazy as reverse

        from creme.creme_core.auth import build_creation_perm

        RGenerator = self.RecurrentGenerator
        reg_item = creme_menu.register_app('recurrents', '/recurrents/').register_item
        reg_item('/recurrents/',                          _(u'Portal of recurrent documents'), 'recurrents')
        reg_item(reverse('recurrents__list_generators'),  _(u'All recurrent generators'),      'recurrents')
        reg_item(reverse('recurrents__create_generator'), RGenerator.creation_label,           build_creation_perm(RGenerator))
