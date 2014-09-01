# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2014  Hybird
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

from django.http import Http404
from django.shortcuts import get_object_or_404
from django.template import RequestContext
from django.utils.translation import ugettext as _

from creme.creme_core.auth.decorators import login_required
from creme.creme_core.models import SettingValue
from creme.creme_core.views.generic import inner_popup
from creme.creme_core.utils import jsonify

from ..forms.setting import SettingForm
from ..blocks import settings_block


@login_required
def edit(request, svalue_id):
    svalue = get_object_or_404(SettingValue, pk=svalue_id)

    if svalue.key.hidden:
        raise Http404('You can not edit a SettingValue which is hidden.')

    if svalue.user_id is not None:
        raise Http404('You can not edit a SettingValue which belongs to a user.')

    user = request.user

    user.has_perm_to_admin_or_die(svalue.key.app_label)

    if request.method == 'POST':
        form = SettingForm(instance=svalue, user=user, data=request.POST)

        if form.is_valid():
            form.save()
    else:
        form = SettingForm(instance=svalue, user=user)

    return inner_popup(request,
                       'creme_core/generics/blockform/edit_popup.html',
                       {'form':  form,
                        'title': _(u'Edit "%s"') % svalue.key.description,
                       },
                       is_valid=form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                      )

@login_required
@jsonify
def reload_block(request, app_name):
    request.user.has_perm_to_admin_or_die(app_name)

    context = RequestContext(request)
    context['app_name'] =  app_name

    return [(settings_block.id_, settings_block.detailview_display(context))]
