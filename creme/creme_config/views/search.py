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
from django.shortcuts import render
from django.conf import settings

from creme.creme_core.views.generic import add_model_with_popup, edit_model_with_popup
from creme.creme_core.models import SearchConfigItem, SearchField
from creme.creme_core.utils import get_from_POST_or_404

from creme.creme_config.forms.search import SearchEditForm, SearchAddForm


@login_required
@permission_required('creme_config.can_admin')
def add(request):
    return add_model_with_popup(request, SearchAddForm, _(u'New search configuration'))

@login_required
@permission_required('creme_config')
def portal(request):
    return render(request, 'creme_config/search_portal.html',
                  {'SHOW_HELP': settings.SHOW_HELP},#TODO:Context processor ?
                 )

@login_required
@permission_required('creme_config.can_admin')
def edit(request, search_config_id):
    return edit_model_with_popup(request, {'pk': search_config_id}, SearchConfigItem, SearchEditForm)

@login_required
@permission_required('creme_config.can_admin')
def delete(request):
    search_cfg_id = get_from_POST_or_404(request.POST, 'id')

    SearchConfigItem.objects.filter(id=search_cfg_id).delete()
    SearchField.objects.filter(search_config_item=search_cfg_id).delete()

    return HttpResponse()
