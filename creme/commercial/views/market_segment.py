# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2017  Hybird
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

import logging

from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.utils.translation import ugettext as _

from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.views import generic

from ..forms import market_segment as segment_forms
from ..models import MarketSegment


logger = logging.getLogger(__name__)


@login_required
@permission_required('commercial')
def add(request):
    return generic.add_model_with_popup(request, segment_forms.MarketSegmentForm,
                                        title=_(u'New market segment'),
                                        submit_label=_(u'Save the market segment'),
                                       )


@login_required
@permission_required('commercial')
def edit(request, segment_id):
    return generic.edit_model_with_popup(request, {'id': segment_id}, MarketSegment,
                                         segment_forms.MarketSegmentForm,
                                        )


@login_required
@permission_required('commercial')
def listview(request):
    return render(request, 'commercial/list_segments.html',
                  context={'bricks_reload_url': reverse('creme_core__reload_bricks')},
                 )


@login_required
@permission_required('commercial')
def delete(request, segment_id):
    if MarketSegment.objects.count() < 2:
        raise ConflictError(_(u"You can't delete the last segment."))

    segment = get_object_or_404(MarketSegment, id=segment_id)

    if segment.property_type is None:
        raise ConflictError(u"You can't delete this specific segment.")

    try:
        return generic.add_model_with_popup(request, segment_forms.SegmentReplacementForm,
                                            _(u'Delete and replace «%s»') % segment,
                                            initial={'segment_to_delete': segment},
                                            submit_label=_(u'Replace'),
                                           )
    except Exception:
        logger.exception('Error in MarketSegment deletion view')
        return HttpResponse(_(u"You can't delete this segment."), status=400)
