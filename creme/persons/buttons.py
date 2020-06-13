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

from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from creme import persons
from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.gui.button_menu import Button
from creme.creme_core.models import Relation

from . import constants

Contact = persons.get_contact_model()
Organisation = persons.get_organisation_model()


class CrmButton(Button):
    __managed_orga   = False
    relation_type_id = 'OVERLOADME'
    template_name    = 'persons/buttons/become.html'
    # what             = 'OVERLOADME'
    # url_name         = 'OVERLOADME'

    def ok_4_display(self, entity):
        # TODO: only one query ??
        self.__managed_orga = Organisation.objects.filter_managed_by_creme()
        already_linked_pk = Relation.objects.filter(type=self.relation_type_id,
                                                    subject_entity=entity,
                                                   ) \
                                            .values_list('object_entity_id', flat=True)
        self.__managed_orga = self.__managed_orga.exclude(pk__in=already_linked_pk)

        return bool(self.__managed_orga)

    def get_ctypes(self):
        return (Contact, Organisation)

    def render(self, context):
        context['managed_orga'] = self.__managed_orga
        # context['what'] = self.what
        context['verbose_name'] = self.verbose_name
        # context['become_url'] = reverse(self.url_name, args=(context['object'].id,))
        context['rtype_id'] = self.relation_type_id

        return super().render(context)


class BecomeCustomerButton(CrmButton):
    id_              = Button.generate_id('persons', 'become_customer')
    verbose_name     = _('Transform into a customer')
    relation_type_id = constants.REL_SUB_CUSTOMER_SUPPLIER
    # what = 'customer'
    # url_name = 'persons__become_customer'


class BecomeProspectButton(CrmButton):
    id_              = Button.generate_id('persons', 'become_prospect')
    verbose_name     = _('Transform into a prospect')
    relation_type_id = constants.REL_SUB_PROSPECT
    # what = 'prospect'
    # url_name = 'persons__become_prospect'


class BecomeSuspectButton(CrmButton):
    id_              = Button.generate_id('persons', 'become_suspect')
    verbose_name     = _('Transform into a suspect')
    relation_type_id = constants.REL_SUB_SUSPECT
    # what = 'suspect'
    # url_name = 'persons__become_suspect'


class BecomeInactiveButton(CrmButton):
    id_              = Button.generate_id('persons', 'become_inactive')
    verbose_name     = _('Transform into an inactive customer')
    relation_type_id = constants.REL_SUB_INACTIVE
    # what = 'inactive_customer'
    # url_name = 'persons__become_inactive_customer'


class BecomeSupplierButton(CrmButton):
    id_              = Button.generate_id('persons', 'become_supplier')
    verbose_name     = _('Transform into a supplier')
    relation_type_id = constants.REL_OBJ_CUSTOMER_SUPPLIER
    # what = 'supplier'
    # url_name = 'persons__become_supplier'


class AddLinkedContactButton(Button):
    id_           = Button.generate_id('persons', 'add_linked_contact')
    verbose_name  = _('Create a related contact')
    template_name = 'persons/buttons/add-linked-contact.html'
    permission    = cperm(Contact)  # TODO: 'persons.addrelated_contact' ??

    def get_ctypes(self):
        return (Organisation,)

    def render(self, context):
        context['contact_link_perm'] = context['user'].has_perm_to_link(Contact)

        return super().render(context)
