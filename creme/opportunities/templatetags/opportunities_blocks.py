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

from django.template import Library

from opportunities.blocks import (linked_contacts_block, responsibles_block,
                                  linked_products_block, linked_services_block,
                                  quotes_block, sales_orders_block, invoices_block,
                                  linked_product_lines_block, linked_service_lines_block)


register = Library()

@register.inclusion_tag('creme_core/templatetags/registered_blocks.html', takes_context=True)
def get_contacts(context):
    return {'blocks': [linked_contacts_block.detailview_display(context)]}

@register.inclusion_tag('creme_core/templatetags/registered_blocks.html', takes_context=True)
def get_products(context):
    return {'blocks': [linked_products_block.detailview_display(context)]}

@register.inclusion_tag('creme_core/templatetags/registered_blocks.html', takes_context=True)
def get_services(context):
    return {'blocks': [linked_services_block.detailview_display(context)]}

@register.inclusion_tag('creme_core/templatetags/registered_blocks.html', takes_context=True)
def get_responsibles(context):
    return {'blocks': [responsibles_block.detailview_display(context)]}

@register.inclusion_tag('creme_core/templatetags/registered_blocks.html', takes_context=True)
def get_quotes(context):
    return {'blocks': [quotes_block.detailview_display(context)]}

@register.inclusion_tag('creme_core/templatetags/registered_blocks.html', takes_context=True)
def get_sales_orders(context):
    return {'blocks': [sales_orders_block.detailview_display(context)]}

@register.inclusion_tag('creme_core/templatetags/registered_blocks.html', takes_context=True)
def get_invoices(context):
    return {'blocks': [invoices_block.detailview_display(context)]}


@register.inclusion_tag('creme_core/templatetags/registered_blocks.html', takes_context=True)
def get_opportproduct_lines(context):
    return {'blocks': [linked_product_lines_block.detailview_display(context)]}

@register.inclusion_tag('creme_core/templatetags/registered_blocks.html', takes_context=True)
def get_opportservice_lines(context):
    return {'blocks': [linked_service_lines_block.detailview_display(context)]}
