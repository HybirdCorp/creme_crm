# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2014  Hybird
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

import logging

from django.conf import settings

from creme.creme_core.models import SettingValue

from .constants import USER_THEME_NAME, USER_TIMEZONE


logger = logging.getLogger(__name__)


def generate_portal_url(app_name):
    return '/creme_config/%s/portal/' % app_name

def get_user_theme(request):
    user = request.user

    if user.is_anonymous():
        return settings.DEFAULT_THEME

    session = request.session
    theme_name = session.get('usertheme')

    if theme_name is None:
        try:
            #sv = SettingValue.objects.get(user=user, key=USER_THEME_NAME)
            sv = SettingValue.objects.get(user=user, key_id=USER_THEME_NAME)
        except SettingValue.DoesNotExist:
            pass
        else:
            value = sv.value
            if any(value == names[0] for names in settings.THEMES):
                theme_name = value
            else:
                logger.warn('Invalid theme "%s" -> deleted', value)
                sv.delete()

        if theme_name is None:
            #sk = SettingKey.objects.get(pk=USER_THEME_NAME)
            theme_name = settings.DEFAULT_THEME
            #sv = SettingValue.objects.create(user=user, key=sk, value=theme_name)
            SettingValue.objects.create(user=user, key_id=USER_THEME_NAME, value=theme_name)

        session['usertheme'] = theme_name

    return theme_name

def get_user_timezone_config(user):
    try:
        #sv = SettingValue.objects.get(user=user, key=USER_TIMEZONE)
        sv = SettingValue.objects.get(user=user, key_id=USER_TIMEZONE)
    except SettingValue.DoesNotExist:
        sv = None
        value = settings.TIME_ZONE
    else:
        value = sv.value

    return value, sv
