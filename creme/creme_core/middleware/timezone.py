# -*- coding: utf-8 -*-

# Based on the official django doc:
# https://docs.djangoproject.com/en/1.4/topics/i18n/timezones/#selecting-the-current-time-zone

#NB: do not 'from django.utils.timezone import activate as activate_tz' because it is harder to unit test
from django.utils import timezone

from creme.creme_config.utils import get_user_timezone_config


_TZ_KEY = 'usertimezone'

class TimezoneMiddleware(object):
    def process_request(self, request):
        session = request.session
        tz = session.get(_TZ_KEY)

        if not tz and not request.user.is_anonymous():
            value, setting_value = get_user_timezone_config(request.user)
            if setting_value:
                session[_TZ_KEY] = tz = value
            #session[_TZ_KEY] = tz = get_user_timezone_config(request.user)[0]
        if tz:
            timezone.activate(tz)
