# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2016  Hybird
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

from django.shortcuts import render

from creme.creme_core.auth.decorators import login_required
from creme.creme_core.utils import jsonify

from ..forms.user_settings import UserThemeForm, UserTimeZoneForm

# NB: no special permissions needed (user can only view/change its own settings)


@login_required
def view(request):
    user = request.user

    return render(request, 'creme_config/user_settings.html',
                  {  # user
                   # 'theme_form': UserThemeForm(user).as_span(),
                   # 'tz_form':    UserTimeZoneForm(user).as_span(),
                   'theme_form': UserThemeForm(user=user, instance=user).as_span(),
                   'tz_form':    UserTimeZoneForm(user=user, instance=user).as_span(),
                  }
                 )


@login_required
@jsonify
# def _set_usersetting(request, form_cls, session_key):
def _set_usersetting(request, form_cls):
    user = request.user

    if request.method == 'POST':
        # form = form_cls(user=request.user, data=request.POST)
        form = form_cls(instance=user, user=user, data=request.POST)

        if form.is_valid():
            # request.session[session_key] = form.save()
            form.save()

            return {}
    else:
        # form = form_cls(user=request.user)
        form = form_cls(instance=user, user=user)

    return {'form': form.as_span()}


def set_theme(request):
    # return _set_usersetting(request, UserThemeForm, 'usertheme')
    return _set_usersetting(request, UserThemeForm)


def set_timezone(request):
    # return _set_usersetting(request, UserTimeZoneForm, 'usertimezone')
    return _set_usersetting(request, UserTimeZoneForm)
