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


class CTIConfig(CremeAppConfig):
    default = True
    name = 'creme.cti'
    verbose_name = _('Computer Telephony Integration')
    dependencies = ['creme.persons', 'creme.activities']
    credentials = CremeAppConfig.CRED_NONE

    def register_bricks(self, brick_registry):
        from . import bricks

        brick_registry.register(bricks.CallersBrick)

    def register_fields_config(self, fields_config_registry):
        from creme import persons

        fields_config_registry.register_needed_fields(
            'cti', persons.get_contact_model(),
            'phone', 'mobile',
        ).register_needed_fields(
            'cti', persons.get_organisation_model(),
            'phone',
        )

    def register_field_printers(self, field_printers_registry):
        from creme.creme_core.models.fields import PhoneField

        from . import utils

        # field_printers_registry.register(PhoneField, utils.print_phone)
        field_printers_registry.register(PhoneField, utils.print_phone_html)
