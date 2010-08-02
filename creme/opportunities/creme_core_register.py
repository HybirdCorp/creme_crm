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

from opportunities.models import Opportunity
from opportunities.buttons import linked_opportunity_button
from opportunities.blocks import *


creme_registry.register_app('opportunities', _(u'Opportunité'), '/opportunities')
creme_registry.register_entity_models(Opportunity)

creme_menu.register_app('opportunities', '/opportunities/', 'Opportunités de vente')
reg_menu = creme_menu.register_menu
reg_menu('opportunities', '/opportunities/opportunities',   'Lister les opportunités') ##unicode ????????
reg_menu('opportunities', '/opportunities/opportunity/add', 'Ajouter une opportunité')

button_registry.register(linked_opportunity_button)

block_registry.register(linked_contacts_block, linked_products_block, linked_services_block,
                        responsibles_block, quotes_block, sales_orders_block, invoices_block)
