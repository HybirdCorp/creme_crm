# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

# import warnings

from django.utils.translation import ugettext_lazy as _

from .constants import UUID_SANDBOX_SUPERUSERS
from .gui.button_menu import Button


class Restrict2SuperusersButton(Button):
    id_           = Button.generate_id('creme_core', 'restrict_2_superusers')
    verbose_name  = _(u'Restrict to superusers')
    template_name = 'creme_core/buttons/restrict-to-superusers.html'

    def render(self, context):
        sandbox = context['object'].sandbox
        context['sandbox_uuid'] = str(sandbox.uuid) if sandbox else None
        context['UUID_SANDBOX_SUPERUSERS'] = UUID_SANDBOX_SUPERUSERS

        return super(Restrict2SuperusersButton, self).render(context)
