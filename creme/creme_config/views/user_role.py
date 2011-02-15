# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template.context import RequestContext
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required, permission_required

from creme_core.models import UserRole
from creme_core.views.generic import add_entity, inner_popup
from creme_core.utils import get_from_POST_or_404

from creme_config.forms.user_role import UserRoleCreateForm, UserRoleEditForm, AddCredentialsForm, DefaultCredsForm


PORTAL_URL = '/creme_config/role/portal/'

#TODO: inner_popups not used because they do not manage very well 'empty' *ChoiceField (POST contains 'null' value)

##TODO: add a generic view add_model() ??
@login_required
@permission_required('creme_config.can_admin')
def add(request):
    return add_entity(request, UserRoleCreateForm, PORTAL_URL)
    #if request.method == 'POST':
        #roleform = UserRoleCreateForm(request.POST)

        #if roleform.is_valid():
            #roleform.save()
    #else:
        #roleform = UserRoleCreateForm()

    #return inner_popup(request, 'creme_core/generics/blockform/add_popup2.html',
                       #{
                        #'form':  roleform,
                        #'title': _(u'New role'),
                       #},
                       #is_valid=roleform.is_valid(),
                       #reload=False,
                       #delegate_reload=True,
                       #context_instance=RequestContext(request))

#TODO: add a generic view edit_model() ??
@login_required
@permission_required('creme_config.can_admin')
def edit(request, role_id):
    role = get_object_or_404(UserRole, pk=role_id)

    if request.method == 'POST':
        roleform = UserRoleEditForm(user=request.user, data=request.POST, instance=role)

        if roleform.is_valid():
            roleform.save()
            return HttpResponseRedirect(PORTAL_URL) #
    else:
        roleform = UserRoleEditForm(user=request.user, instance=role)

    #return inner_popup(request, 'creme_core/generics/blockform/edit_popup.html',
                       #{
                        #'form':  roleform,
                        #'title': _(u'Edit %s') % role,
                       #},
                       #is_valid=roleform.is_valid(),
                       #reload=False,
                       #delegate_reload=True,
                       #context_instance=RequestContext(request))
    return render_to_response('creme_core/generics/blockform/edit.html',
                              {'form': roleform},
                              context_instance=RequestContext(request))

@login_required
@permission_required('creme_config.can_admin')
def add_credentials(request, role_id):
    role = get_object_or_404(UserRole, pk=role_id)

    if request.method == 'POST':
        add_form = AddCredentialsForm(role, user=request.user, data=request.POST)

        if add_form.is_valid():
            add_form.save()
    else:
        add_form = AddCredentialsForm(role, user=request.user)

    return inner_popup(request, 'creme_core/generics/blockform/edit_popup.html',
                       {
                        'form':  add_form,
                        'title': _(u'Add creddentials to <%s>') % role,
                       },
                       is_valid=add_form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                       context_instance=RequestContext(request)
                      )

@login_required
@permission_required('creme_config')
def portal(request):
    return render_to_response('creme_config/user_role_portal.html', {},
                              context_instance=RequestContext(request))

@login_required
@permission_required('creme_config.can_admin')
def delete(request):
    role = get_object_or_404(UserRole, pk=get_from_POST_or_404(request.POST, 'id'))
    role.delete()

    return HttpResponse()

@login_required
@permission_required('creme_config.can_admin')
def set_default_creds(request):
    if request.method == 'POST':
        form = DefaultCredsForm(user=request.user, data=request.POST)

        if form.is_valid():
            form.save()
    else:
        form = DefaultCredsForm(user=request.user)

    return inner_popup(request, 'creme_core/generics/blockform/edit_popup.html',
                       {
                        'form':  form,
                        'title': _(u'Edit default credentials'),
                       },
                       is_valid=form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                       context_instance=RequestContext(request)
                      )
