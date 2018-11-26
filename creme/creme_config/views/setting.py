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

# import warnings

# from django.http import Http404
# from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _  # ugettext

# from creme.creme_core.auth.decorators import login_required
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.models import SettingValue
from creme.creme_core.views.generic import CremeModelEditionPopup  # inner_popup

from ..forms.setting import SettingForm


# TODO: move to generic_views.py ??

# @login_required
# def edit(request, svalue_id):
#     svalue = get_object_or_404(SettingValue, pk=svalue_id)
#     if svalue.key.hidden:
#         raise Http404('You can not edit a SettingValue which is hidden.')
#
#     user = request.user
#     user.has_perm_to_admin_or_die(svalue.key.app_label)
#
#     if request.method == 'POST':
#         form = SettingForm(instance=svalue, user=user, data=request.POST)
#
#         if form.is_valid():
#             form.save()
#     else:
#         form = SettingForm(instance=svalue, user=user)
#
#     return inner_popup(request,
#                        'creme_core/generics/blockform/edit_popup.html',
#                        {'form':  form,
#                         'title': ugettext(u'Edit «{}»').format(svalue.key.description),
#                        },
#                        is_valid=form.is_valid(),
#                        reload=False,
#                        delegate_reload=True,
#                       )
class SettingValueEdition(CremeModelEditionPopup):
    model = SettingValue
    form_class = SettingForm
    pk_url_kwarg = 'svalue_id'
    title = _('Edit «{key}»')

    def get_object(self, *args, **kwargs):
        svalue = super().get_object(*args, **kwargs)

        if svalue.key.hidden:
            raise ConflictError('You can not edit a SettingValue which is hidden.')

        self.request.user.has_perm_to_admin_or_die(svalue.key.app_label)

        return svalue

    def get_title_format_data(self):
        data = super().get_title_format_data()
        data['key'] = self.object.key.description

        return data
