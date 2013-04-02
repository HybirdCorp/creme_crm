# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2012  Hybird
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

from django.contrib.auth.decorators import login_required
#from django.template.context import RequestContext
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.views.generic.popup import inner_popup

from creme.activesync.forms.user_settings import UserSettingsConfigForm


#TODO: to be tested
@login_required
def edit_own_mobile_settings(request):
#TODO: If user change his email, all already synced items to be resync with the new email address
    if request.method == 'POST':
        form = UserSettingsConfigForm(request.user, request.POST)

        if form.is_valid():
            form.save()
    else:
        form = UserSettingsConfigForm(user=request.user)

    return inner_popup(request, 'creme_core/generics/blockform/add_popup2.html', #TODO: edit_popup.html ??
                       {'form':   form,
                        'title': _(u'Edit your mobile synchronization configuration'),
                       },
                       is_valid=form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                       #context_instance=RequestContext(request)
                      )
