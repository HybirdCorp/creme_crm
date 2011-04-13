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
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _

from creme_core.views.generic.add import add_model_with_popup

from creme_config.models.setting import SettingValue
from activesync.forms.mobile_sync import MobileSyncForm

from activesync.constants import MAPI_SERVER_URL, MAPI_DOMAIN, MAPI_SERVER_SSL

@login_required
@permission_required('creme_config.can_admin')
def edit(request):
    #TODO: Why 404???
    server_url    = get_object_or_404(SettingValue, key__id=MAPI_SERVER_URL)
    server_domain = get_object_or_404(SettingValue, key__id=MAPI_DOMAIN)
    server_ssl    = get_object_or_404(SettingValue, key__id=MAPI_SERVER_SSL)

    initial = {'url': server_url.value, 'domain': server_domain.value, 'ssl': server_ssl.value}

    return add_model_with_popup(request, MobileSyncForm,
                                title=_(u'Edit default mobile synchronization configuration'),
                                initial=initial)

