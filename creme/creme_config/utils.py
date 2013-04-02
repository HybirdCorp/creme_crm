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

from django.conf import settings

from creme.creme_config.constants import USER_THEME_NAME
from creme.creme_config.models import SettingValue, SettingKey


def generate_portal_url(app_name):
    return '/creme_config/%s/portal/' % app_name

def get_user_theme(user, request=None):
    default_theme = settings.DEFAULT_THEME
    if user.is_anonymous():
        return default_theme

    if request is not None:
        if request.session.get('usertheme') is not None:
            return request.session['usertheme']

    theme_name = None
    try:
        sv = SettingValue.objects.get(user=user, key=USER_THEME_NAME)
        if sv.value not in [names[0] for names in settings.THEMES]:
            SettingValue.objects.filter(user=user, key=USER_THEME_NAME).delete()
            raise SettingValue.DoesNotExist
        theme_name = sv.value

    except SettingValue.DoesNotExist:
        sk = SettingKey.objects.get(pk=USER_THEME_NAME)
        sv = SettingValue.objects.create(user=user, key=sk)
        sv.value = default_theme
        sv.save()
        theme_name = default_theme

    if request is not None:
        request.session['usertheme'] = theme_name

    return theme_name
