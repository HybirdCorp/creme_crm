# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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

from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.gui.button_menu import Button

from . import get_opportunity_model


class LinkedOpportunityButton(Button):
    id_ = Button.generate_id('opportunities', 'linked_opportunity')
    verbose_name = _('Create a linked opportunity')
    description = _(
        'This button displays the creation form for opportunities. '
        'The current entity is pre-selected to be the target of the created opportunity.\n'
        'App: Opportunities'
    )
    template_name = 'opportunities/buttons/linked-opp.html'
    # permission = cperm(get_opportunity_model())
    permissions = cperm(get_opportunity_model())

    def get_ctypes(self):
        from creme import persons
        return (
            persons.get_organisation_model(),
            persons.get_contact_model(),
        )
