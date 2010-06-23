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

from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType

from creme_core.models import Relation
from creme_core.entities_access.functions_for_permissions import edit_object_or_die

from documents.constants import REL_SUB_CURRENT_DOC

from billing.models import Quote

from opportunities.models import Opportunity


@login_required
def set_current_quote(request, opp_id, quote_id):
    opp = get_object_or_404(Opportunity, pk=opp_id)

    die_status = edit_object_or_die(request, opp)
    if die_status:
        return die_status

    quote = get_object_or_404(Quote, pk=quote_id)
    #TODO: credential for quote ??? link credential instead ?????

    #TODO: modify the existing relation instead of delete it ???
    ct = ContentType.objects.get_for_model(Quote)

    #TODO. delete() directly on the filter ????
    for relation in Relation.objects.filter(object_entity=opp, type=REL_SUB_CURRENT_DOC, subject_entity__entity_type=ct):
        relation.delete()

    Relation.create(quote, REL_SUB_CURRENT_DOC, opp)

    return HttpResponseRedirect(opp.get_absolute_url())
