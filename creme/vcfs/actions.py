# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2018-2019  Hybird
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

from django.urls.base import reverse
from django.utils.translation import gettext_lazy as _

from creme import persons
from creme.creme_core.gui.actions import UIAction


class GenerateVcfAction(UIAction):
    id = UIAction.generate_id('vcfs', 'export')
    model = persons.get_contact_model()

    type = 'redirect'
    url_name = 'vcfs__export'

    label = _('Generate a VCF')
    icon = 'download'

    @property
    def url(self):
        return reverse(self.url_name, args=(self.instance.id,))

    @property
    def is_enabled(self):
        return self.user.has_perm_to_view(self.instance)

    # TODO ?
    # @property
    # def help_text(self):
    #     return _('Download as a VCF file ....')
