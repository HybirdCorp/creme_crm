# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2022  Hybird
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

from creme import persons
from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.gui.button_menu import Button
from creme.creme_core.models import Relation

from . import constants

Contact = persons.get_contact_model()
Organisation = persons.get_organisation_model()


class CrmButton(Button):
    __managed_orga = False
    relation_type_id = 'OVERRIDE'
    template_name = 'persons/buttons/become.html'

    def ok_4_display(self, entity):
        # TODO: only one query ??
        already_linked_pk = Relation.objects.filter(
            type=self.relation_type_id,
            subject_entity=entity,
        ).values_list('object_entity_id', flat=True)
        self.__managed_orga = (
            Organisation.objects
                        .filter_managed_by_creme()
                        .exclude(pk__in=already_linked_pk)
                        .exclude(id=entity.id)
        )

        return bool(self.__managed_orga)

    def get_ctypes(self):
        return Contact, Organisation

    def render(self, context):
        context['managed_orga'] = self.__managed_orga
        context['verbose_name'] = self.verbose_name
        context['rtype_id'] = self.relation_type_id

        return super().render(context)


class BecomeCustomerButton(CrmButton):
    id_ = Button.generate_id('persons', 'become_customer')
    verbose_name = _('Transform into a customer')
    description = _(
        'This button links the current entity to an Organisation managed by Creme, '
        'using the relationship type «is a customer of».\n'
        'App: Accounts and Contacts'
    )
    relation_type_id = constants.REL_SUB_CUSTOMER_SUPPLIER


class BecomeProspectButton(CrmButton):
    id_ = Button.generate_id('persons', 'become_prospect')
    verbose_name = _('Transform into a prospect')
    description = _(
        'This button links the current entity to an Organisation managed by Creme, '
        'using the relationship type «is a prospect of».\n'
        'App: Accounts and Contacts'
    )
    relation_type_id = constants.REL_SUB_PROSPECT


class BecomeSuspectButton(CrmButton):
    id_ = Button.generate_id('persons', 'become_suspect')
    verbose_name = _('Transform into a suspect')
    description = _(
        'This button links the current entity to an Organisation managed by Creme, '
        'using the relationship type «is a suspect of».\n'
        'App: Accounts and Contacts'
    )
    relation_type_id = constants.REL_SUB_SUSPECT


class BecomeInactiveButton(CrmButton):
    id_ = Button.generate_id('persons', 'become_inactive')
    verbose_name = _('Transform into an inactive customer')
    description = _(
        'This button links the current entity to an Organisation managed by Creme, '
        'using the relationship type «is an inactive customer of».\n'
        'App: Accounts and Contacts'
    )
    relation_type_id = constants.REL_SUB_INACTIVE


class BecomeSupplierButton(CrmButton):
    id_ = Button.generate_id('persons', 'become_supplier')
    verbose_name = _('Transform into a supplier')
    description = _(
        'This button links the current entity to an Organisation managed by Creme, '
        'using the relationship type «is a supplier of».\n'
        'App: Accounts and Contacts'
    )
    relation_type_id = constants.REL_OBJ_CUSTOMER_SUPPLIER


class AddLinkedContactButton(Button):
    id_ = Button.generate_id('persons', 'add_linked_contact')
    verbose_name = _('Create a related contact')
    description = _(
        'This button displays the creation form for contacts. '
        'The current organisation is pre-selected to be linked to the created contact.\n'
        'It is useful to create employees for example '
        '(it can be done through the employees block too).\n'
        'App: Accounts and Contacts'
    )
    template_name = 'persons/buttons/add-linked-contact.html'
    # permission = cperm(Contact)
    permissions = cperm(Contact)  # TODO: 'persons.addrelated_contact' ??

    def get_ctypes(self):
        return (Organisation,)

    def render(self, context):
        context['contact_link_perm'] = context['user'].has_perm_to_link(Contact)

        return super().render(context)
