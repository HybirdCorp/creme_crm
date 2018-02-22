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

from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.gui.button_menu import Button
from creme.creme_core.models import Relation

from creme import persons
from . import constants


Contact = persons.get_contact_model()
Organisation = persons.get_organisation_model()


class CrmButton(Button):
    __managed_orga   = False
    relation_type_id = 'OVERLOADME'
    # template_name    = 'persons/templatetags/button_become.html'
    template_name    = 'persons/buttons/become.html'
    what             = 'OVERLOADME'
    url_name         = 'OVERLOADME'

    def ok_4_display(self, entity):
        # TODO: only one query ??
        self.__managed_orga = Organisation.get_all_managed_by_creme()
        already_linked_pk = Relation.objects.filter(type=self.relation_type_id,
                                                    subject_entity=entity,
                                                    is_deleted=False,
                                                   ) \
                                            .values_list('object_entity_id', flat=True)
        self.__managed_orga = self.__managed_orga.exclude(pk__in=already_linked_pk)

        return bool(self.__managed_orga)

    def get_ctypes(self):
        return (Contact, Organisation)

    def render(self, context):
        context['managed_orga'] = self.__managed_orga
        context['what'] = self.what
        context['verbose_name'] = self.verbose_name
        context['become_url'] = reverse(self.url_name, args=(context['object'].id,))

        return super(CrmButton, self).render(context)


class BecomeCustomerButton(CrmButton):
    id_              = Button.generate_id('persons', 'become_customer')
    verbose_name     = _(u'Transform into a customer')
    relation_type_id = constants.REL_SUB_CUSTOMER_SUPPLIER
    what = 'customer'
    url_name = 'persons__become_customer'


class BecomeProspectButton(CrmButton):
    id_              = Button.generate_id('persons', 'become_prospect')
    verbose_name     = _(u'Transform into a prospect')
    relation_type_id = constants.REL_SUB_PROSPECT
    what = 'prospect'
    url_name = 'persons__become_prospect'


class BecomeSuspectButton(CrmButton):
    id_              = Button.generate_id('persons', 'become_suspect')
    verbose_name     = _(u'Transform into a suspect')
    relation_type_id = constants.REL_SUB_SUSPECT
    what = 'suspect'
    url_name = 'persons__become_suspect'


class BecomeInactiveButton(CrmButton):
    id_              = Button.generate_id('persons', 'become_inactive')
    verbose_name     = _(u'Transform into an inactive customer')
    relation_type_id = constants.REL_SUB_INACTIVE
    what = 'inactive_customer'
    url_name = 'persons__become_inactive_customer'


class BecomeSupplierButton(CrmButton):
    id_              = Button.generate_id('persons', 'become_supplier')
    verbose_name     = _(u'Transform into a supplier')
    relation_type_id = constants.REL_OBJ_CUSTOMER_SUPPLIER
    what = 'supplier'
    url_name = 'persons__become_supplier'

    def get_ctypes(self):
        return (Organisation,)


class AddLinkedContactButton(Button):
    id_           = Button.generate_id('persons', 'add_linked_contact')
    verbose_name  = _(u'Create a related contact')
    # template_name = 'persons/templatetags/button_add_linked_contact.html'
    template_name = 'persons/buttons/add-linked-contact.html'
    permission    = cperm(Contact)  # TODO: 'persons.addrelated_contact' ??

    def get_ctypes(self):
        return (Organisation,)

    def render(self, context):
        context['contact_link_perm'] = context['user'].has_perm_to_link(Contact)

        return super(AddLinkedContactButton, self).render(context)


# DEPRECATED ---------------------
become_customer_button    = BecomeCustomerButton()
become_prospect_button    = BecomeProspectButton()
become_suspect_button     = BecomeSuspectButton()
become_inactive_button    = BecomeInactiveButton()
become_supplier_button    = BecomeSupplierButton()
add_linked_contact_button = AddLinkedContactButton()

button_list = (
        become_customer_button,
        become_prospect_button,
        become_suspect_button,
        become_inactive_button,
        become_supplier_button,
        add_linked_contact_button,
    )
