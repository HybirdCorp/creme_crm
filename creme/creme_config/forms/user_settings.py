################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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

from django.contrib.auth import get_user_model
from django.urls.base import reverse
from django.utils.translation import gettext_lazy as _

from creme.creme_core.forms.base import CremeModelForm
from creme.creme_core.forms.widgets import PrettySelect

User = get_user_model()


class MenuSetting(PrettySelect):
    def __init__(self, url, choices=()):
        self.url = url
        super().__init__(attrs={'class': 'user-setting-toggle'}, choices=choices)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context['widget']['attrs']['data-url'] = reverse(self.url)
        return context


class UserThemeForm(CremeModelForm):
    class Meta:
        model = User
        fields = ('theme',)
        widgets = {
            'theme': MenuSetting(url='creme_config__set_user_theme'),
        }
        labels = {'theme': _('Your theme')}


class UserTimeZoneForm(CremeModelForm):
    class Meta:
        model = User
        fields = ('time_zone',)
        widgets = {
            'time_zone': MenuSetting(url='creme_config__set_user_timezone'),
        }
        labels = {'time_zone': _('Your time zone')}


class UserLanguageForm(CremeModelForm):
    class Meta:
        model = User
        fields = ('language',)
        widgets = {
            'language': MenuSetting(url='creme_config__set_user_language'),
        }
        labels = {'language': _('Your language')}


class UserDisplayedNameForm(CremeModelForm):
    class Meta:
        model = User
        fields = ('displayed_name',)
        labels = {'displayed_name': _('How to display your name')}
