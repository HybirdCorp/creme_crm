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

from django.shortcuts import render_to_response
from django.template import RequestContext
from django.contrib.auth.decorators import login_required

from creme_core.gui.last_viewed import add_item_in_last_viewed
from creme_core.entities_access.functions_for_permissions import get_view_or_die, read_object_or_die

from billing.blocks import total_block


#TODO: remove and use view_entity_with_template instead ????
@login_required
@get_view_or_die('billing')
def view_billing_entity(request, object_id, object, path, template='billing/view_billing.html'):
    """
        @Permissions : Acces or Admin to billing app & Read on current object
    """
    die_status = read_object_or_die(request, object)
    if die_status:
        return die_status

    add_item_in_last_viewed(request, object)

    return render_to_response(template,
                              {
                                'object': object,
                                'path':   path,
                              },
                              context_instance=RequestContext(request))


def reload_total(request, document_id):
    return total_block.detailview_ajax(request, document_id)    