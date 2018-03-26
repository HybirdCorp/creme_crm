# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

from django.http import Http404
from django.utils.translation import ugettext as _

from creme.creme_core.auth.decorators import login_required
from creme.creme_core.core.setting_key import user_setting_key_registry
from creme.creme_core.utils import jsonify
from creme.creme_core.views.generic import inner_popup

from ..forms.setting import UserSettingForm
from ..forms.user_settings import UserThemeForm, UserTimeZoneForm
# from ..registry import config_registry

from .portal import _config_portal

# NB: no special permissions needed (user can only view/change its own settings)


@login_required
def view(request):
    from ..registry import config_registry

    user = request.user

    return _config_portal(
            request, 'creme_config/user_settings.html',
            theme_form=UserThemeForm(user=user, instance=user).as_span(),
            tz_form=UserTimeZoneForm(user=user, instance=user).as_span(),
            apps_usersettings_bricks=list(config_registry.user_bricks),
    )


@login_required
@jsonify
def _set_usersetting(request, form_cls):
    user = request.user

    if request.method == 'POST':
        form = form_cls(instance=user, user=user, data=request.POST)

        if form.is_valid():
            form.save()

            return {}
    else:
        form = form_cls(instance=user, user=user)

    return {'form': form.as_span()}


def set_theme(request):
    return _set_usersetting(request, UserThemeForm)


def set_timezone(request):
    return _set_usersetting(request, UserTimeZoneForm)


@login_required
def edit_setting_value(request, skey_id):
    try:
        skey = user_setting_key_registry[skey_id]
    except KeyError:
        raise Http404('This key is invalid')

    if skey.hidden:
        raise Http404('You can not edit a UserSettingValue which is hidden.')

    if request.method == 'POST':
        form = UserSettingForm(skey=skey, user=request.user, data=request.POST)

        if form.is_valid():
            form.save()
    else:
        form = UserSettingForm(skey=skey, user=request.user)

    return inner_popup(request,
                       'creme_core/generics/blockform/edit_popup.html',
                       {'form':  form,
                        'title': _(u'Edit «%s»') % skey.description,
                       },
                       is_valid=form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                      )
