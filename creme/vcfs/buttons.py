# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2020  Hybird
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

from creme.creme_core.gui.button_menu import Button
from creme.persons import get_contact_model


class GenerateVcfButton(Button):
    id_ = Button.generate_id('vcfs', 'generate_vcf')
    verbose_name = _('Generate a VCF file')
    description = _(
        'This button generates a VCF file from the current contact.\n'
        'App: VCF'
    )
    template_name = 'vcfs/buttons/generate.html'

    def get_ctypes(self):
        return (get_contact_model(),)
