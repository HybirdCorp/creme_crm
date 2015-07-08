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


class CTIConfig(CremeAppConfig):
    name = 'creme.cti'
    verbose_name = _(u'Computer Telephony Integration')
    dependencies = ['creme.persons', 'creme.activities']

    def register_creme_app(self, creme_registry):
        creme_registry.register_app('cti', _(u'Computer Telephony Integration'),
                                    '/cti', credentials=creme_registry.CRED_NONE,
                                   )

    def register_field_printers(self, field_printers_registry):
        from creme.creme_core.models.fields  import PhoneField

        from .utils import print_phone

        field_printers_registry.register(PhoneField, print_phone)
