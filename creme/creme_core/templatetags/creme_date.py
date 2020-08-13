# -*- coding: utf-8 -*-

################################################################################
#
# Copyright (c) 2009-2020 Hybird
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
################################################################################

from django import template
from django.utils.translation import ngettext

register = template.Library()


@register.filter(name='date_timedelta_pprint')
def timedelta_pprint(timedelta_):
    days = timedelta_.days

    if days > 0:
        return ngettext('{number} day', '{number} days', days).format(number=days)

    hours, hour_remain = divmod(timedelta_.seconds, 3600)

    if hours > 0:
        return ngettext('{number} hour', '{number} hours', hours).format(number=hours)

    minutes, seconds = divmod(hour_remain, 60)

    if minutes > 0:
        return ngettext('{number} minute', '{number} minutes', minutes).format(number=minutes)

    return ngettext('{number} second', '{number} seconds', seconds).format(number=seconds)
