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

from django.db.transaction import atomic
from django.http import Http404
from django.shortcuts import get_object_or_404
# from django.utils.translation import ugettext as _
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.auth.decorators import login_required
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.core.setting_key import user_setting_key_registry
from creme.creme_core.views import generic
from creme.creme_core.views.decorators import jsonify
# from creme.creme_core.views.generic import inner_popup

from ..forms import user_settings as settings_forms
from ..forms.setting import UserSettingForm
# from ..registry import config_registry

# from .portal import _config_portal

# NB: no special permissions needed (user can only view/change its own settings)


# @login_required
# def view(request):
#     from ..registry import config_registry
#
#     user = request.user
#
#     return _config_portal(
#             request, 'creme_config/user_settings.html',
#             theme_form=settings_forms.UserThemeForm(user=user, instance=user).as_span(),
#             tz_form=settings_forms.UserTimeZoneForm(user=user, instance=user).as_span(),
#             apps_usersettings_bricks=list(config_registry.user_bricks),
#     )
class UserSettings(generic.BricksView):
    template_name = 'creme_config/user_settings.html'

    def get_context_data(self, **kwargs):
        from ..registry import config_registry

        user = self.request.user

        context = super().get_context_data(**kwargs)
        context['theme_form'] = settings_forms.UserThemeForm(user=user, instance=user).as_span()
        context['tz_form'] = settings_forms.UserTimeZoneForm(user=user, instance=user).as_span()
        context['apps_usersettings_bricks'] = list(config_registry.user_bricks)

        return context


@login_required
@jsonify
def _set_usersetting(request, form_cls):
    user = request.user

    if request.method == 'POST':
        with atomic():
            form = form_cls(
                instance=get_object_or_404(user.__class__
                                               ._default_manager
                                               .select_for_update(),
                                           pk=user.pk,
                                          ),
                user=user,
                data=request.POST,
            )

            if form.is_valid():
                form.save()

                return {}
    else:
        form = form_cls(instance=user, user=user)

    return {'form': form.as_span()}


def set_theme(request):
    return _set_usersetting(request, settings_forms.UserThemeForm)


def set_timezone(request):
    return _set_usersetting(request, settings_forms.UserTimeZoneForm)


# @login_required
# def edit_setting_value(request, skey_id):
#     try:
#         skey = user_setting_key_registry[skey_id]
#     except KeyError as e:
#         raise Http404('This key is invalid') from e
#
#     if skey.hidden:
#         raise Http404('You can not edit a UserSettingValue which is hidden.')
#
#     if request.method == 'POST':
#         form = UserSettingForm(skey=skey, user=request.user, data=request.POST)
#
#         if form.is_valid():
#             form.save()
#     else:
#         form = UserSettingForm(skey=skey, user=request.user)
#
#     return inner_popup(request,
#                        'creme_core/generics/blockform/edit_popup.html',
#                        {'form':  form,
#                         'title': _('Edit «{}»').format(skey.description),
#                        },
#                        is_valid=form.is_valid(),
#                        reload=False,
#                        delegate_reload=True,
#                       )
class UserSettingValueEdition(generic.CremeEditionPopup):
    form_class = UserSettingForm
    key_id_url_kwarg = 'skey_id'
    title = _('Edit «{key}»')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.skey = None

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['skey'] = self.get_skey()

        return kwargs

    def get_skey(self):
        skey = self.skey

        if skey is None:
            try:
                skey = user_setting_key_registry[self.kwargs[self.key_id_url_kwarg]]
            except KeyError as e:
                raise Http404('This key is invalid') from e

            if skey.hidden:
                raise ConflictError('You can not edit a UserSettingValue which is hidden.')

            self.skey = skey

        return skey

    def get_title_format_data(self):
        data = super().get_title_format_data()
        data['key'] = self.get_skey().description

        return data
