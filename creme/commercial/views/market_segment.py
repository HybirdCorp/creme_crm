# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2020  Hybird
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

from django.db import DatabaseError
from django.http import HttpResponse
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.views import generic

from ..forms import market_segment as segment_forms
from ..models import MarketSegment

logger = logging.getLogger(__name__)


class SegmentCreation(generic.CremeModelCreationPopup):
    model = MarketSegment
    form_class = segment_forms.MarketSegmentForm
    permissions = 'commercial'


class SegmentEdition(generic.CremeModelEditionPopup):
    model = MarketSegment
    form_class = segment_forms.MarketSegmentForm
    pk_url_kwarg = 'segment_id'
    permissions = 'commercial'


class Segments(generic.BricksView):
    template_name = 'commercial/list_segments.html'
    permissions = 'commercial'
    bricks_reload_url_name = 'creme_core__reload_bricks'


class SegmentDeletion(generic.CremeModelEditionPopup):
    # model = MarketSegment
    queryset = MarketSegment.objects.exclude(property_type=None)
    form_class = segment_forms.SegmentReplacementForm
    template_name = 'creme_core/generics/blockform/delete-popup.html'
    pk_url_kwarg = 'segment_id'
    permissions = 'commercial'
    title = _('Delete and replace «{object}»')
    submit_label = _('Replace')

    def check_view_permissions(self, user):
        super().check_view_permissions(user=user)

        if MarketSegment.objects.count() < 2:
            raise ConflictError(gettext("You can't delete the last segment."))

    def post(self, *args, **kwargs):
        try:
            return super().post(*args, **kwargs)
        except DatabaseError as e:
            logger.exception('Error in MarketSegment deletion view')

            return HttpResponse(
                gettext('You cannot delete this segment [original error: {}].').format(e),
                status=400,
            )
