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

from django.utils.translation import ugettext_lazy as _
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import get_object_or_404, render_to_response
from django.template.context import RequestContext
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User

from creme_core.entities_access.functions_for_permissions import get_view_or_die
from creme_core.constants import DROIT_MODULE_EST_ADMIN

from creme_config.forms.user_settings import UserSettingsConfigForm
from creme_config.forms.user import  UserAddForm, UserChangePwForm, UserEditForm
from creme_config.blocks import users_block


portal_url = '/creme_config/user/portal/'

@login_required
@get_view_or_die('creme_config', DROIT_MODULE_EST_ADMIN)
def change_password(request, user_id):
    """
        @Permissions : Admin to creme_config app
    """
    user = get_object_or_404(User, pk=user_id)

    if request.POST:
        entity_form = UserChangePwForm(request.POST, initial={'user': user})
        if entity_form.is_valid():
            entity_form.save()
            return HttpResponseRedirect(portal_url)
    else:
        entity_form = UserChangePwForm(initial={'user': user})

    return render_to_response('creme_config/users/add_user.html',
                              {'form': entity_form},
                              context_instance=RequestContext(request))

@login_required
@get_view_or_die('creme_config', DROIT_MODULE_EST_ADMIN)
def add(request):
    """
        @Permissions : Admin to creme_config app
    """
    if request.POST :
        entity_form = UserAddForm(request.POST)
        if entity_form.is_valid():
            entity_form.save()
            return HttpResponseRedirect(portal_url)
    else:
        entity_form = UserAddForm()

    return render_to_response('creme_config/users/add_user.html',
                              {'form': entity_form},
                              context_instance=RequestContext(request))

@login_required
@get_view_or_die('creme_config')
def portal(request):
    """
        @Permissions : Acces OR Admin to creme_config app
    """
    return render_to_response('creme_config/users/portal.html',
                              {},
                              context_instance=RequestContext(request))

@login_required
@get_view_or_die('creme_config', DROIT_MODULE_EST_ADMIN)
def delete(request):
    """
        @Permissions : Admin to creme_config app
    """
    user =  get_object_or_404(User, pk=request.POST.get('id'))
    if user.can_be_deleted():
        user.delete()
        return HttpResponse()
    else:
        return HttpResponse(unicode(_(u'%s ne peut être effacé à cause des ses dépendances.' % user)),status=403)

@login_required
@get_view_or_die('creme_config', DROIT_MODULE_EST_ADMIN)
def edit(request, user_id):
    """
        @Permissions : Admin to creme_config app
    """
    user = get_object_or_404(User, pk=user_id)

    if request.POST :
        userform = UserEditForm(request.POST,instance=user)
        if userform.is_valid():
            userform.save()
            return HttpResponseRedirect(portal_url)
    else:
        userform = UserEditForm(instance=user)

    return render_to_response('creme_core/generics/form/edit.html',
                              {'form': userform},
                              context_instance=RequestContext(request))

@login_required
@get_view_or_die('creme_config', DROIT_MODULE_EST_ADMIN)
def edit_own_settings(request):
    """
        @Permissions : Admin to creme_config app
    """
    user = get_object_or_404(User, pk=request.user.id)

    if request.POST :
        settings_form = UserSettingsConfigForm(user, request.POST)
        if settings_form.is_valid():
            settings_form.save()
        return HttpResponseRedirect('/')
    else:
        settings_form = UserSettingsConfigForm(user)

    return render_to_response('creme_core/generics/form/edit.html',
                              {'form': settings_form},
                              context_instance=RequestContext(request))

@login_required
@get_view_or_die('creme_config')
def reload_block(request):
    return users_block.detailview_ajax(request)
