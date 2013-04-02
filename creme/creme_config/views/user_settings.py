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

from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from creme.creme_core.utils import jsonify

from creme.creme_config.forms.user_settings import UserThemeForm

#NB: no special permissions needed (user can only view/change its settings)

@login_required
def view(request):
    return render(request, 'creme_config/user_settings.html',
                 {'user':        request.user,
                  'themes_form': UserThemeForm(request.user).as_span(),
                 }
                )

@jsonify
@login_required
def edit_theme(request):
    if request.method == 'POST':
        theme_form = UserThemeForm(user=request.user, data=request.POST)

        if theme_form.is_valid():
            theme_form.save()
            del request.session['usertheme']
    else:
        theme_form = UserThemeForm(user=request.user)

    return {'form': theme_form.as_span()}
