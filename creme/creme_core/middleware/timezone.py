# -*- coding: utf-8 -*-

# Based on the official django doc:
# https://docs.djangoproject.com/en/1.4/topics/i18n/timezones/#selecting-the-current-time-zone

from django.conf import settings
# NB: do not 'from django.utils.timezone import activate as activate_tz'
#     because it is harder to unit test
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin


class TimezoneMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # NB: AnonymousUser has no 'time_zone' attribute (we need it for the login view)
        tz = getattr(request.user, 'time_zone', None)

        if tz and tz != settings.TIME_ZONE:
            timezone.activate(tz)
