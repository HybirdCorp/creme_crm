# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2013  Hybird
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

import pytz

from django.conf import settings
from django.forms.fields import ChoiceField
from django.forms.widgets import Select
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.forms.base import CremeForm
from creme.creme_core.models import SettingValue
from creme.creme_core.utils import update_model_instance
from creme.creme_core.utils.media import get_current_theme

from ..constants import USER_THEME_NAME, USER_TIMEZONE
from ..utils import get_user_timezone_config


class UserThemeForm(CremeForm):
    theme = ChoiceField(label=_(u"Choose your theme"), choices=settings.THEMES,
                        widget=Select(attrs={'onchange': 'creme.ajax.json.ajaxFormSubmit($(this.form), function() {creme.utils.reload(window);});'}),
                        #help_text=_(u"Think to reload the page once you changed the theme."),
                       )

    def __init__(self, *args, **kwargs):
        super(UserThemeForm, self).__init__(*args, **kwargs)
        self.fields['theme'].initial = get_current_theme()

    def save(self, *args, **kwargs):
        theme = self.cleaned_data['theme']

        #TODO: SettingValue.objects.get_or_create (update_model_instance if 'not created')
        try:
            #sv = SettingValue.objects.get(user=self.user, key=USER_THEME_NAME)
            sv = SettingValue.objects.get(user=self.user, key_id=USER_THEME_NAME)
        except SettingValue.DoesNotExist:
            #sk = SettingKey.objects.get(pk=USER_THEME_NAME)
            #SettingValue.objects.create(user=self.user, key=sk, value=theme)
            SettingValue.objects.create(user=self.user, key_id=USER_THEME_NAME, value=theme)
        else:
            update_model_instance(sv, value=theme)

        return theme


class UserTimeZoneForm(CremeForm):
    time_zone = ChoiceField(label=_(u'Choose your time zone'),
                            choices=[(tz, tz) for tz in pytz.common_timezones],
                            #widget=Select(attrs={'onchange': 'creme.ajax.json.ajaxFormSubmit($(this.form));'}),
                            widget=Select(attrs={'onchange': 'creme.ajax.json.ajaxFormSubmit($(this.form), function() {creme.utils.reload(window);});'}),
                           )

    def __init__(self, *args, **kwargs):
        super(UserTimeZoneForm, self).__init__(*args, **kwargs)
        self.fields['time_zone'].initial, self.setting_value = \
            get_user_timezone_config(self.user)

    def save(self, *args, **kwargs):
        time_zone = self.cleaned_data['time_zone']

        if not self.setting_value:
            #sk = SettingKey.objects.get(pk=USER_TIMEZONE)
            #SettingValue.objects.create(user=self.user, key=sk, value=time_zone)
            SettingValue.objects.create(user=self.user, key_id=USER_TIMEZONE, value=time_zone)
        else:
            update_model_instance(self.setting_value, value=time_zone)

        return time_zone
