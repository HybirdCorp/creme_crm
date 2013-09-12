# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2013  Hybird
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

from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required

from creme.creme_core.views.decorators import POST_only
from creme.creme_core.models import Relation

from creme.billing.models import Quote

from ..constants import REL_SUB_CURRENT_DOC
from ..models import Opportunity


@login_required
@permission_required('opportunities')
@POST_only
def current_quote(request, opp_id, quote_id, action):

    user = request.user

    has_perm_or_die = user.has_perm_to_link_or_die if action == 'set_current' else user.has_perm_to_unlink_or_die

    opp = get_object_or_404(Opportunity, pk=opp_id)
    has_perm_or_die(opp)

    quote = get_object_or_404(Quote, pk=quote_id)
    has_perm_or_die(quote)

    kwargs = {'subject_entity': quote,
              'type_id': REL_SUB_CURRENT_DOC,
              'object_entity': opp,
              'user': user
              }

    relations = Relation.objects.filter(**kwargs)

    if action == 'set_current':
        if not relations:
            Relation.objects.create(**kwargs)
    else:  # action == 'unset_current':
        relations.delete()

    if request.is_ajax():
        return HttpResponse("", mimetype="text/javascript")

    return redirect(opp)
