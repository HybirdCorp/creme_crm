# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2017  Hybird
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

# import pytz

# from django.conf import settings
from django.contrib.auth import get_user_model
# from django.forms.fields import ChoiceField
from django.forms.widgets import Select
from django.utils.translation import ugettext_lazy as _

# from creme.creme_core.forms.base import CremeForm
from creme.creme_core.forms.base import CremeModelForm
# from creme.creme_core.models import SettingValue
# from creme.creme_core.utils import update_model_instance
# from creme.creme_core.utils.media import get_current_theme

# # from ..constants import USER_THEME_NAME, USER_TIMEZONE
# from ..utils import get_user_timezone_config


User = get_user_model()


def _build_select():
    return Select(attrs={'onchange': 'creme.ajax.json.ajaxFormSubmit($(this.form), '
                                                                    'function() {creme.utils.reload(window);}'
                                                                   ');'
                        },
                 )


# class UserThemeForm(CremeForm):
#     theme = ChoiceField(label=_(u"Choose your theme"), choices=settings.THEMES,
#                         widget=Select(attrs={'onchange': 'creme.ajax.json.ajaxFormSubmit($(this.form), function() {creme.utils.reload(window);});'}),
#                        )
#
#     def __init__(self, *args, **kwargs):
#         super(UserThemeForm, self).__init__(*args, **kwargs)
#         self.fields['theme'].initial = get_current_theme()
#
#     def save(self, *args, **kwargs):
#         theme = self.cleaned_data['theme']
#
#         # todo: SettingValue.objects.get_or_create (update_model_instance if 'not created')
#         try:
#             sv = SettingValue.objects.get(user=self.user, key_id=USER_THEME_NAME)
#         except SettingValue.DoesNotExist:
#             SettingValue.objects.create(user=self.user, key_id=USER_THEME_NAME, value=theme)
#         else:
#             update_model_instance(sv, value=theme)
#
#         return theme
class UserThemeForm(CremeModelForm):
    class Meta:
        model = User
        fields = ('theme',)
        widgets = {'theme': _build_select()}
        labels = {'theme': _(u'Choose your theme')}


# class UserTimeZoneForm(CremeForm):
#     time_zone = ChoiceField(label=_(u'Choose your time zone'),
#                             choices=[(tz, tz) for tz in pytz.common_timezones],
#                             widget=Select(attrs={'onchange': 'creme.ajax.json.ajaxFormSubmit($(this.form), function() {creme.utils.reload(window);});'}),
#                            )
#
#     def __init__(self, *args, **kwargs):
#         super(UserTimeZoneForm, self).__init__(*args, **kwargs)
#         self.fields['time_zone'].initial, self.setting_value = \
#             get_user_timezone_config(self.user)
#
#     def save(self, *args, **kwargs):
#         time_zone = self.cleaned_data['time_zone']
#
#         if not self.setting_value:
#             SettingValue.objects.create(user=self.user, key_id=USER_TIMEZONE, value=time_zone)
#         else:
#             update_model_instance(self.setting_value, value=time_zone)
#
#         return time_zone
class UserTimeZoneForm(CremeModelForm):
    class Meta:
        model = User
        fields = ('time_zone',)
        widgets = {'time_zone': _build_select()}
        labels = {'time_zone': _(u'Choose your time zone')}
