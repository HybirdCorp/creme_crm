# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2019  Hybird
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
from django.utils.translation import ugettext_lazy as _
from django.shortcuts import get_object_or_404

from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.models import HistoryConfigItem
from creme.creme_core.utils import get_from_POST_or_404
from creme.creme_core.views.generic import BricksView

from ..forms.history import HistoryConfigForm

from .base import ConfigCreation


class HistoryConfigCreation(ConfigCreation):
    model = HistoryConfigItem
    form_class = HistoryConfigForm
    title = _('New relation types')


class Portal(BricksView):
    template_name = 'creme_config/history_portal.html'


@login_required
@permission_required('creme_core.can_admin')
def delete(request):
    get_object_or_404(HistoryConfigItem, pk=get_from_POST_or_404(request.POST, 'id')).delete()

    return HttpResponse()
