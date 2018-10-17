# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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
# import warnings

from django.db import DatabaseError
# from django.urls import reverse
from django.http import HttpResponse
# from django.shortcuts import render, get_object_or_404
from django.utils.translation import ugettext_lazy as _, ugettext

# from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.views import generic

from ..forms import market_segment as segment_forms
from ..models import MarketSegment


logger = logging.getLogger(__name__)


# @login_required
# @permission_required('commercial')
# def add(request):
#     return generic.add_model_with_popup(request, segment_forms.MarketSegmentForm,
#                                         title=_('New market segment'),
#                                         submit_label=_('Save the market segment'),
#                                        )


class SegmentCreation(generic.CremeModelCreationPopup):
    model = MarketSegment
    form_class = segment_forms.MarketSegmentForm
    permissions = 'commercial'


# @login_required
# @permission_required('commercial')
# def edit(request, segment_id):
#     return generic.edit_model_with_popup(request, {'id': segment_id}, MarketSegment,
#                                          segment_forms.MarketSegmentForm,
#                                         )
class SegmentEdition(generic.CremeModelEditionPopup):
    model = MarketSegment
    form_class = segment_forms.MarketSegmentForm
    pk_url_kwarg = 'segment_id'
    permissions = 'commercial'


# @login_required
# @permission_required('commercial')
# def listview(request):
#     return render(request, 'commercial/list_segments.html',
#                   context={'bricks_reload_url': reverse('creme_core__reload_bricks')},
#                  )
class Segments(generic.BricksView):
    template_name = 'commercial/list_segments.html'
    permissions = 'commercial'
    bricks_reload_url_name = 'creme_core__reload_bricks'


# @login_required
# @permission_required('commercial')
# def delete(request, segment_id):
#     if MarketSegment.objects.count() < 2:
#         raise ConflictError(ugettext("You can't delete the last segment."))
#
#     segment = get_object_or_404(MarketSegment, id=segment_id)
#
#     if segment.property_type is None:
#         raise ConflictError("You can't delete this specific segment.")
#
#     try:
#         return generic.add_model_with_popup(request, segment_forms.SegmentReplacementForm,
#                                             ugettext('Delete and replace «{}»').format(segment),
#                                             initial={'segment_to_delete': segment},
#                                             submit_label=_('Replace'),
#                                            )
#     except Exception:
#         logger.exception('Error in MarketSegment deletion view')
#         return HttpResponse(_("You can't delete this segment."), status=400)
class SegmentDeletion(generic.CremeModelEditionPopup):
    # model = MarketSegment
    queryset = MarketSegment.objects.exclude(property_type=None)
    form_class = segment_forms.SegmentReplacementForm
    template_name = 'creme_core/generics/blockform/delete_popup.html'
    pk_url_kwarg = 'segment_id'
    permissions = 'commercial'
    title_format = _('Delete and replace «{}»')
    submit_label = _('Replace')

    def check_view_permissions(self, user):
        super().check_view_permissions(user=user)

        if MarketSegment.objects.count() < 2:
            raise ConflictError(ugettext("You can't delete the last segment."))

    def post(self, *args, **kwargs):
        try:
            return super().post(*args, **kwargs)
        except DatabaseError as e:
            logger.exception('Error in MarketSegment deletion view')

            return HttpResponse(
                ugettext('You cannot delete this segment [original error: {}].').format(e),
                status=400,
            )
