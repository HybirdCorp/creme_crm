################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2021-2025  Hybird
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

from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from creme import persons
from creme.creme_core.auth import build_list_perm
from creme.creme_core.gui import menu

Contact = persons.get_contact_model()
Organisation = persons.get_organisation_model()


class UserContactEntry(menu.MenuEntry):
    id = 'persons-user_contact'
    label = _("*User's contact*")

    def render(self, context):
        user = context['user']
        contact = user.linked_contact

        return (
            format_html(
                '<a href="{url}">{user}</a>',
                url=contact.get_absolute_url(), user=user,
            )
            if contact and user.has_perm_to_view(contact) else
            format_html(
                '<span class="ui-creme-navigation-text-entry forbidden">{user}</span>',
                user=user,
            )
        )


class ContactsEntry(menu.ListviewEntry):
    id = 'persons-contacts'
    model = Contact


class OrganisationsEntry(menu.ListviewEntry):
    id = 'persons-organisations'
    model = Organisation


class CustomersEntry(menu.FixedURLEntry):
    id = 'persons-lead_customers'
    # TODO: ignore disabled relation types (wait for relation-types cache?)
    label = _('My customers / prospects / suspects')
    url_name = 'persons__leads_customers'
    # permissions = 'persons'
    permissions = build_list_perm(Organisation)


class ContactCreationEntry(menu.CreationEntry):
    id = 'persons-create_contact'
    model = Contact


class OrganisationCreationEntry(menu.CreationEntry):
    id = 'persons-create_organisation'
    model = Organisation
