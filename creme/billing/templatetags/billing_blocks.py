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

from billing.blocks import product_lines_block, service_lines_block, total_block


register = Library()


@register.inclusion_tag('creme_core/templatetags/registered_blocks.html', takes_context=True)
def get_product_lines(context):
    return {'blocks': [product_lines_block.detailview_display(context)]}

@register.inclusion_tag('creme_core/templatetags/registered_blocks.html', takes_context=True)
def get_service_lines(context):
    return {'blocks': [service_lines_block.detailview_display(context)]}


@register.inclusion_tag('creme_core/templatetags/registered_blocks.html', takes_context=True)
def get_total(context):
    return {'blocks': [total_block.detailview_display(context)]}
