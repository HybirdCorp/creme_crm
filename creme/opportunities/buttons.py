################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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

from django.apps import apps
from django.utils.translation import gettext_lazy as _

from creme.creme_core.auth import build_creation_perm
from creme.creme_core.gui.button_menu import Button

from . import get_opportunity_model

Opportunity = get_opportunity_model()


class LinkedOpportunityButton(Button):
    id = Button.generate_id('opportunities', 'linked_opportunity')
    verbose_name = _('Create a linked opportunity')
    description = _(
        'This button displays the creation form for opportunities. '
        'The current entity is pre-selected to be the target of the created opportunity.\n'
        'App: Opportunities'
    )
    template_name = 'opportunities/buttons/linked-opp.html'
    permissions = build_creation_perm(Opportunity)

    def check_permissions(self, *, entity, request):
        super().check_permissions(entity=entity, request=request)
        request.user.has_perm_to_link_or_die(entity)

    def get_ctypes(self):
        from creme import persons
        return (
            persons.get_organisation_model(),
            persons.get_contact_model(),
        )


button_classes: list[type[Button]] = [
    LinkedOpportunityButton,
]


if apps.is_installed('creme.activities'):
    from creme.activities import get_activity_model

    Activity = get_activity_model()

    class AddUnsuccessfulPhoneCallButton(Button):
        id = Button.generate_id('opportunities', 'add_unsuccessful_phonecall')
        verbose_name = _('Create an unsuccessful phone call')
        template_name = 'opportunities/buttons/add-unsuccessful-phonecall.html'
        permissions = build_creation_perm(Activity)
        description = _(
            'This button creates a short phone call (kind of activity) which was '
            'not successful (in order to keep an history).\n'
            'All the contacts linked to the current Opportunity participate in '
            'the created call, & you too.\n'
            'The fields values can be set in the configuration of «Activities».\n'
            'App: Opportunities'
        )
        dependencies = (Activity,)

        def check_permissions(self, *, entity, request):
            super().check_permissions(entity=entity, request=request)
            request.user.has_perm_to_link_or_die(entity)

        def get_ctypes(self):
            return [Opportunity]

    button_classes.append(AddUnsuccessfulPhoneCallButton)
