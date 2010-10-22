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
from django.contrib.auth.decorators import login_required, permission_required

from creme_core.gui.last_viewed import add_item_in_last_viewed


#TODO: remove and use view_entity_with_template instead ????
@login_required
@permission_required('billing')
def view_billing_entity(request, entity, path, template='billing/view_billing.html', can_download=True):
    entity.can_view_or_die(request.user)

    add_item_in_last_viewed(request, entity)

    return render_to_response(template,
                              {
                                'object':       entity,
                                'path':         path,
                                'can_download': can_download,
                              },
                              context_instance=RequestContext(request))
