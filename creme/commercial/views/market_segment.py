# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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

from django.template import RequestContext
from django.shortcuts import render_to_response
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required, permission_required

from creme_core.views.generic import inner_popup

from commercial.forms.market_segment import MarketSegmentForm


#TODO: generic view: add_model_with_popup ???
@login_required
@permission_required('commercial')
def add(request):
    if request.method == 'POST':
        segment_form = MarketSegmentForm(user=request.user, data=request.POST)

        if segment_form.is_valid():
            segment_form.save()
    else:
        segment_form = MarketSegmentForm(user=request.user)

    return inner_popup(request, 'creme_core/generics/blockform/add_popup2.html',
                       {
                        'form':   segment_form,
                        'title':  _(u'New market segment'),
                       },
                       is_valid=segment_form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                       context_instance=RequestContext(request))

@login_required
@permission_required('commercial')
def listview(request):
    return render_to_response('commercial/list_segments.html', {}, context_instance=RequestContext(request))
