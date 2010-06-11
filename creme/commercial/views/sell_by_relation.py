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
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.contrib.auth.decorators import login_required

from creme_core.entities_access.functions_for_permissions import get_view_or_die
from creme_core.models.entity import CremeEntity

from commercial.models import SellByRelation
from commercial.forms.sell_by_relation import SellByRelationEditForm


@login_required
@get_view_or_die('commercial')
def edit(request, relation_id):
    relation = get_object_or_404(SellByRelation, pk=relation_id)

    if request.POST:
        relationform = SellByRelationEditForm(request.POST, instance=relation)
        if relationform.is_valid():
            relationform.save()
            relation.subject_id
            entity = CremeEntity.objects.get(id=relation.subject_id)
            return HttpResponseRedirect(entity.get_absolute_url())
    else:
        relationform = SellByRelationEditForm(instance=relation)

    return render_to_response('creme_core/generics/blockform/edit.html', {'form': relationform},
                              context_instance=RequestContext(request))
