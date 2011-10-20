# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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

from django.conf import settings
from django.utils.translation import ugettext as _
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import get_object_or_404, render_to_response
from django.template.context import RequestContext
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User
from creme_core.utils import jsonify

from creme_core.views.generic import add_model_with_popup, edit_model_with_popup

from creme_config.forms.user_settings import UserSettingsConfigForm, UserThemeForm
from creme_config.forms.user import UserAddForm, UserChangePwForm, UserEditForm, TeamCreateForm, TeamEditForm, UserAssignationForm


@login_required
@permission_required('creme_config.can_admin')
def change_password(request, user_id):
    return edit_model_with_popup(request, {'pk': user_id}, User, UserChangePwForm, _(u'Change password for <%s>'))

@login_required
@permission_required('creme_config.can_admin')
def add(request):
    return add_model_with_popup(request, UserAddForm, _(u'New user'))

@login_required
@permission_required('creme_config.can_admin')
def add_team(request):
    return add_model_with_popup(request, TeamCreateForm, _(u'New team'))

@login_required
@permission_required('creme_config')
def portal(request):
    return render_to_response('creme_config/user_portal.html', {},
                              context_instance=RequestContext(request))

@login_required
@permission_required('creme_config.can_admin')
def edit(request, user_id):
    return edit_model_with_popup(request, {'pk': user_id}, User, UserEditForm)

@login_required
@permission_required('creme_config.can_admin')
def edit_team(request, user_id):
    return edit_model_with_popup(request, {'pk': user_id, 'is_team': True}, User, TeamEditForm)

@login_required #no special permission needed
def edit_own_settings(request):
    user = request.user

    if request.method == 'POST':
        settings_form = UserSettingsConfigForm(user2edit=user, user=user, data=request.POST)

        if settings_form.is_valid():
            settings_form.save()
            return HttpResponseRedirect('/creme_config/user/view/settings/')
    else:
        settings_form = UserSettingsConfigForm(user2edit=user, user=user)

    return render_to_response('creme_core/generics/form/edit.html',
                              {'form': settings_form},
                              context_instance=RequestContext(request))

@login_required #no special permission needed
def view_own_settings(request):
    return render_to_response('creme_config/user_settings.html',
                              {
                                'user':        request.user,
                                'themes_form': UserThemeForm(request.user).as_span(),
                              },
                              context_instance=RequestContext(request))

@jsonify
@login_required
def edit_theme(request):
    user = request.user

    if request.method == 'POST':
        theme_form = UserThemeForm(user=user, data=request.POST)

        if theme_form.is_valid():
            theme_form.save()
            del request.session['usertheme']
    else:
        theme_form = UserThemeForm(user=user)

    return {'form': theme_form.as_span()}

@login_required
@permission_required('creme_config.can_admin')
def assign_user_n_delete(request, user_id, is_team):
    user_to_delete = get_object_or_404(User, pk=user_id)

    if User.objects.filter(is_team=False).count() == 1:
        return HttpResponse(_(u"You can't delete the last user."), status=400)

    if is_team and not user_to_delete.is_team:
        return HttpResponse(_(u"You have to select a team."), status=400)

    return add_model_with_popup(request, UserAssignationForm, _(u'Delete %s and assign his files to user') % user_to_delete,
                                initial={'user_to_delete': user_to_delete, 'is_team': is_team})

