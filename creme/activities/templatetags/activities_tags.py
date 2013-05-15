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

from django import template
from django.utils.translation import ugettext as _
from django.utils.html import escape

from creme.creme_core.constants import ICON_SIZE_MAP
from creme.creme_core.utils.media import creme_media_themed_url

from ..constants import *
from ..models import ActivityType


register = template.Library()

_ICON_MAP = {ACTIVITYTYPE_MEETING:      'meeting',
             ACTIVITYTYPE_PHONECALL:    'phone',
             ACTIVITYTYPE_TASK:         'task',
            }

#TODO : test
@register.simple_tag
def get_activity_icon(activity_type_id, size='big'):
    """{% get_activity_icon activity 'big' %}"""
    path = creme_media_themed_url("images/%s_%s.png" % (_ICON_MAP.get(activity_type_id, 'calendar'),
                                                        ICON_SIZE_MAP[size],
                                                       )
                                 )

    try:
        title = escape(ActivityType.objects.get(pk=activity_type_id).name)
    except ActivityType.DoesNotExist:
        title = _('Error')

    return u'<img src="%(src)s" alt="%(title)s" title="%(title)s" />' % {
                'src':   path,
                'title': title,
            }
