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

from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.contenttypes.models import ContentType

from creme.creme_core.models import Relation

from creme.billing.models import Quote

from ..constants import REL_SUB_CURRENT_DOC
from ..models import Opportunity


@login_required
@permission_required('opportunities')
def set_current_quote(request, opp_id, quote_id):
    if request.method != 'POST':
        raise Http404('This view accepts only POST method')

    #NB: we do not check if the relation to the current quote (if it exists) can be deleted (can_unlink_or_die())
    opp = get_object_or_404(Opportunity, pk=opp_id)
    user = request.user

    has_perm_or_die = user.has_perm_to_link_or_die
    has_perm_or_die(opp)

    quote = get_object_or_404(Quote, pk=quote_id)
    has_perm_or_die(quote)

    #TODO: modify the existing relation instead of delete it ???
    ct = ContentType.objects.get_for_model(Quote)

    #TODO. delete() directly on the filter ????
    for relation in Relation.objects.filter(object_entity=opp.id, type=REL_SUB_CURRENT_DOC, subject_entity__entity_type=ct):
        relation.delete()

    Relation.objects.create(subject_entity=quote, type_id=REL_SUB_CURRENT_DOC,
                            object_entity=opp, user=user
                           )

    if request.is_ajax():
        return HttpResponse("", mimetype="text/javascript")

    return HttpResponseRedirect(opp.get_absolute_url())
