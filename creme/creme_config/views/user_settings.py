# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2020  Hybird
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

from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _

from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.core.setting_key import user_setting_key_registry
from creme.creme_core.http import CremeJsonResponse
from creme.creme_core.views import generic

from .. import registry
from ..forms import user_settings as settings_forms
from ..forms.setting import UserSettingForm

# NB: no special permissions needed (user can only view/change its own settings)


class UserSettings(generic.BricksView):
    template_name = 'creme_config/user_settings.html'

    config_registry = registry.config_registry

    def get_context_data(self, **kwargs):
        user = self.request.user

        context = super().get_context_data(**kwargs)
        context['theme_form'] = settings_forms.UserThemeForm(
            user=user, instance=user,
        ).as_span()
        context['tz_form'] = settings_forms.UserTimeZoneForm(
            user=user, instance=user,
        ).as_span()
        context['language_form'] = settings_forms.UserLanguageForm(
            user=user, instance=user,
        ).as_span()
        context['apps_usersettings_bricks'] = [*self.config_registry.user_bricks]

        return context


# TODO: only POST ?
# TODO: generic class view for ajax+POST ?
class _UserFieldSetting(generic.base.CremeFormView):
    response_class = CremeJsonResponse

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = self.get_user()

        return kwargs

    def get_user(self):
        request = self.request
        user = request.user

        if request.method == 'POST':
            return get_object_or_404(
                user.__class__._default_manager.select_for_update(),
                pk=user.pk,
            )
        else:
            return user

    def form_invalid(self, form):
        return self.response_class({'form': form.as_span()})

    def form_valid(self, form):
        form.save()
        return HttpResponse()

    def get(self, *args, **kwargs):
        return self.response_class({'form': self.get_form().as_span()})


class ThemeSetting(_UserFieldSetting):
    form_class = settings_forms.UserThemeForm


class TimeZoneSetting(_UserFieldSetting):
    form_class = settings_forms.UserTimeZoneForm


class LanguageSetting(_UserFieldSetting):
    form_class = settings_forms.UserLanguageForm


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
