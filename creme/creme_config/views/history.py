# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2012  Hybird
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
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, render

from creme_core.models import HistoryConfigItem
from creme_core.views.generic import add_model_with_popup
from creme_core.utils import get_from_POST_or_404

from creme_config.forms.history import HistoryConfigForm


@login_required
@permission_required('creme_config.can_admin')
def add(request):
    return add_model_with_popup(request, HistoryConfigForm, _(u'New relation types'))

@login_required
@permission_required('creme_config')
def portal(request):
    return render(request, 'creme_config/history_portal.html')

@login_required
@permission_required('creme_config.can_admin')
def delete(request):
    get_object_or_404(HistoryConfigItem, pk=get_from_POST_or_404(request.POST, 'id')).delete()

    return HttpResponse()
