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

from django.contrib.auth.decorators import login_required, permission_required

from django.template.context import RequestContext
from django.shortcuts import get_object_or_404, render_to_response
from django.utils.translation import ugettext_lazy as _
from creme_config.models.setting import SettingValue

from creme_core.views.generic.popup import inner_popup

from creme_config.forms.mobile_sync import MobileSyncForm

from activesync.constants import MAPI_SERVER_URL, MAPI_DOMAIN, MAPI_SERVER_SSL


portal_url = "/creme_config/mobile_synchronization/portal/"

@login_required
@permission_required('creme_config.can_admin')
def portal(request):
    """
        @Permissions : Acces OR Admin to creme_config app
    """
    return render_to_response('creme_config/mobile_sync/portal.html',
                              {
                                
                              },
                              context_instance=RequestContext(request))


#TODO: Use a generic view ?
@login_required
@permission_required('creme_config.can_admin')
def edit(request):
    """
        @Permissions : Admin to creme_config app
    """
    #TODO: Why 404???
    server_url    = get_object_or_404(SettingValue, key__id=MAPI_SERVER_URL)
    server_domain = get_object_or_404(SettingValue, key__id=MAPI_DOMAIN)
    server_ssl    = get_object_or_404(SettingValue, key__id=MAPI_SERVER_SSL)

    initial = {'url': server_url.value, 'domain': server_domain.value, 'ssl': server_ssl.value}

    if request.POST :
        mobile_sync_form = MobileSyncForm(user=request.user, data=request.POST, initial=initial)

        if mobile_sync_form.is_valid():
            mobile_sync_form.save()
    else:
        mobile_sync_form = MobileSyncForm(user=request.user, initial=initial)

    return inner_popup(request, 'creme_core/generics/blockform/add_popup2.html',
                       {
                         'form': mobile_sync_form,
                         'title': _(u'Edit default mobile synchronization configuration'),
                       },
                       is_valid=mobile_sync_form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                       context_instance=RequestContext(request))