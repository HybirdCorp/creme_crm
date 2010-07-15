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

from django.db.models.query_utils import Q
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render_to_response
from django.template.context import RequestContext

from creme_core.views.generic import add_entity
from creme_core.models.authent_role import CremeProfile, CremeRole
from creme_core.entities_access.functions_for_permissions import get_view_or_die
from creme_core.constants import DROIT_MODULE_EST_ADMIN

from persons.models.contact import Contact

from creme_config.forms.profile import ProfileAddForm, ProfileEditForm


@login_required
@get_view_or_die('creme_config', DROIT_MODULE_EST_ADMIN)
def add(request):
    """
        @Permissions : Admin to creme_config app
    """
    return add_entity(request, ProfileAddForm, '/creme_config/profile/portal/', 'creme_core/generics/form/add.html')

@login_required
@get_view_or_die('creme_config', DROIT_MODULE_EST_ADMIN)
def edit(request, profile_id):
    """
        @Permissions : Admin to creme_config app
    """
    profile =  get_object_or_404(CremeProfile, pk=profile_id)

    if request.POST :
        profileform = ProfileEditForm(request.POST, instance=profile)
        if profileform.is_valid():
            profileform.save()
            return HttpResponseRedirect('/creme_config/profile/portal/')
    else:
        profileform = ProfileEditForm(instance=profile)

    return render_to_response('creme_core/generics/form/edit.html', {'form': profileform},
                              context_instance=RequestContext(request))

@login_required
@get_view_or_die('creme_config')
def portal(request):
    """
        @Permissions : Access OR Admin to creme_config app
    """
    role_post = request.POST.get('roles')

    if role_post:
        role_selected  = CremeRole.objects.get(pk=role_post)
        profile_filter = Q(creme_role=role_selected)
    else:
        role_selected  = ""
        profile_filter = Q()

    return render_to_response('creme_config/profile_portal.html',
                              {
                                'profiles':     CremeProfile.objects.filter(profile_filter),
                                'contacts':     dict((c.is_user.id, c) for c in Contact.objects.filter(~Q(is_user=None))),
                                'roles':        CremeRole.objects.all(),
                                'role_post':    role_selected,
                               },
                               context_instance=RequestContext(request ) )

@login_required
@get_view_or_die('creme_config', DROIT_MODULE_EST_ADMIN)
def delete(request, profile_id):
    """
        @Permissions : Admin to creme_config app
    """
    profile = get_object_or_404(CremeProfile, pk=profile_id)
    profile.delete()
    return portal(request)
