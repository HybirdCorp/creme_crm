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

from django.contrib.auth.decorators import login_required

from opportunities.blocks import (linked_contacts_block, responsibles_block,
                                  linked_products_block, linked_services_block,
                                  quotes_block, sales_orders_block, invoices_block)


@login_required
def reload_linked_contacts(request, opp_id):
    return linked_contacts_block.detailview_ajax(request, opp_id)

@login_required
def reload_linked_invoices(request, opp_id):
    return invoices_block.detailview_ajax(request, opp_id)

@login_required
def reload_linked_products(request, opp_id):
    return linked_products_block.detailview_ajax(request, opp_id)

@login_required
def reload_linked_services(request, opp_id):
    return linked_services_block.detailview_ajax(request, opp_id)

@login_required
def reload_linked_quotes(request, opp_id):
    return quotes_block.detailview_ajax(request, opp_id)

@login_required
def reload_linked_salesorders(request, opp_id):
    return sales_orders_block.detailview_ajax(request, opp_id)

@login_required
def reload_responsibles(request, opp_id):
    return responsibles_block.detailview_ajax(request, opp_id)
