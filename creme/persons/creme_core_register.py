# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

from django.utils.translation import ugettext_lazy as _

from creme_core.registry import creme_registry
from creme_core.gui.menu import creme_menu
from creme_core.gui.button_menu import button_registry
from creme_core.gui.block import block_registry

from persons.models import Contact, Organisation
from persons.buttons import (become_customer_button, become_prospect_button, become_suspect_button,
                             become_inactive_button, become_supplier_button, add_linked_contact_button)
from persons.blocks import managers_block, employees_block


creme_registry.register_entity_models(Contact, Organisation)
creme_registry.register_app('persons', _(u'Comptes et contacts'), '/persons')

creme_menu.register_app('persons', '/persons/', 'Comptes et contacts')
reg_menu = creme_menu.register_menu
reg_menu('persons', '/persons/contacts',         'Lister les contacts')
reg_menu('persons', '/persons/leads_customers',  'Mes clients / prospects / suspects')
reg_menu('persons', '/persons/contact/add',      'Ajouter un contact')
reg_menu('persons', '/persons/organisations',    'Lister les sociétés')
reg_menu('persons', '/persons/organisation/add', 'Ajouter une société')


button_registry.register(become_customer_button, become_prospect_button, become_suspect_button,
                         become_inactive_button, become_supplier_button, add_linked_contact_button)

reg_block = block_registry.register
reg_block(managers_block)
reg_block(employees_block)
