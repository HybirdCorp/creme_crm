# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2013  Hybird
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
from django.shortcuts import render, get_object_or_404
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required, permission_required

from creme.creme_core.auth.decorators import superuser_required
from creme.creme_core.models import UserRole, SetCredentials
from creme.creme_core.views.generic import add_model_with_popup, edit_model_with_popup, inner_popup
from creme.creme_core.views.decorators import POST_only
from creme.creme_core.utils import get_from_POST_or_404

from ..forms.user_role import UserRoleCreateForm, UserRoleEditForm, AddCredentialsForm, UserRoleDeleteForm


@login_required
@superuser_required
def add(request):
    return add_model_with_popup(request, UserRoleCreateForm, _(u'New role'))

@login_required
@superuser_required
def edit(request, role_id):
    return edit_model_with_popup(request, {'pk': role_id}, UserRole, UserRoleEditForm)

@login_required
@superuser_required
def add_credentials(request, role_id):
    role = get_object_or_404(UserRole, pk=role_id)

    if request.method == 'POST':
        add_form = AddCredentialsForm(role, user=request.user, data=request.POST)

        if add_form.is_valid():
            add_form.save()
    else:
        add_form = AddCredentialsForm(role, user=request.user)

    return inner_popup(request, 'creme_core/generics/blockform/edit_popup.html',
                       {'form':  add_form,
                        'title': _(u'Add creddentials to <%s>') % role,
                       },
                       is_valid=add_form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                      )

@login_required
@superuser_required
@POST_only
def delete_credentials(request):
    get_object_or_404(SetCredentials, pk=get_from_POST_or_404(request.POST, 'id')).delete()
    return HttpResponse()

@login_required
@permission_required('creme_config')
def portal(request):
    return render(request, 'creme_config/user_role_portal.html')

@login_required
@superuser_required
def delete(request, role_id):
    role = get_object_or_404(UserRole, pk=role_id)

    return add_model_with_popup(request, UserRoleDeleteForm,
                                _(u'Delete role <%s>') % role,
                                initial={'role_to_delete': role},
                               )
