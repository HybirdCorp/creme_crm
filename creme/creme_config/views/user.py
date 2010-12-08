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

from django.utils.translation import ugettext as _
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import get_object_or_404, render_to_response
from django.template.context import RequestContext
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User

from creme_core.utils import get_from_POST_or_404

from creme_config.forms.user_settings import UserSettingsConfigForm
from creme_config.forms.user import UserAddForm, UserChangePwForm, UserEditForm, TeamCreateForm, TeamEditForm


PORTAL_URL = '/creme_config/user/portal/'

@login_required
@permission_required('creme_config.can_admin')
def change_password(request, user_id):
    user = get_object_or_404(User, pk=user_id)

    if request.POST:
        pw_form = UserChangePwForm(request.POST, initial={'user': user})
        if pw_form.is_valid():
            pw_form.save()
            return HttpResponseRedirect(PORTAL_URL)
    else:
        pw_form = UserChangePwForm(initial={'user': user})

    return render_to_response('creme_core/generics/form/edit.html',
                              {'form': pw_form},
                              context_instance=RequestContext(request))

@login_required
@permission_required('creme_config.can_admin')
def _add(request, form_class):
    if request.method == 'POST':
        form = form_class(request.POST)

        if form.is_valid():
            form.save()
            return HttpResponseRedirect(PORTAL_URL)
    else:
        form = form_class()

    return render_to_response('creme_core/generics/blockform/add.html',
                              {'form': form},
                              context_instance=RequestContext(request))

def add(request):
    return _add(request, UserAddForm)

def add_team(request):
    return _add(request, TeamCreateForm)

@login_required
@permission_required('creme_config')
def portal(request):
    return render_to_response('creme_config/user_portal.html', {},
                              context_instance=RequestContext(request))

@login_required
@permission_required('creme_config.can_admin')
def delete(request):
    user = get_object_or_404(User, pk=get_from_POST_or_404(request.POST, 'id'))

    if not user.can_be_deleted():
        return HttpResponse(_(u'%s can not be deleted because of his dependencies.') % user, status=403)

    user.delete()

    return HttpResponse()

@login_required
@permission_required('creme_config.can_admin')
def _edit(request, form_class, instance):
    if request.method == 'POST':
        form = form_class(request.POST, instance=instance)

        if form.is_valid():
            form.save()
            return HttpResponseRedirect(PORTAL_URL)
    else:
        form = form_class(instance=instance)

    return render_to_response('creme_core/generics/blockform/edit.html',
                              {'form': form},
                              context_instance=RequestContext(request))

def edit(request, user_id):
    return _edit(request, UserEditForm, get_object_or_404(User, pk=user_id))

def edit_team(request, user_id):
    return _edit(request, TeamEditForm, get_object_or_404(User, pk=user_id, is_team=True))

@login_required #no special permission needed
def edit_own_settings(request):
    user = get_object_or_404(User, pk=request.user.id)

    if request.method == 'POST':
        settings_form = UserSettingsConfigForm(user, request.POST)
        if settings_form.is_valid():
            settings_form.save()
            return HttpResponseRedirect('/creme_config/user/view/settings/')
    else:
        settings_form = UserSettingsConfigForm(user)

    return render_to_response('creme_core/generics/form/edit.html',
                              {'form': settings_form},
                              context_instance=RequestContext(request))

@login_required #no special permission needed
def view_own_settings(request):
    return render_to_response('creme_config/user_settings.html',
                              {'user': request.user},
                              context_instance=RequestContext(request))

@login_required
@permission_required('creme_config.can_admin')
def delete_team(request):
    team = get_object_or_404(User, pk=get_from_POST_or_404(request.POST, 'id'), is_team=True)

    if not team.can_be_deleted():
        return HttpResponse(_(u'%s can not be deleted because of his dependencies.') % team, status=403)

    team.delete() #no need to update credentials: team is deleted if there are teammates or entities owned

    return HttpResponse()
