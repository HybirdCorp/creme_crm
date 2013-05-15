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

from django.utils.translation import ugettext as _

from creme.creme_core.views.generic.portal import app_portal

from creme.creme_config.utils import generate_portal_url

from ..models import Activity
from ..constants import *


def portal(request):
    act_filter = Activity.objects.filter

    stats = ((_(u"Activities count"),  Activity.objects.count()),
             (_(u"Meetings count"),    act_filter(type=ACTIVITYTYPE_MEETING).count()),
             (_(u"Phone calls count"), act_filter(type=ACTIVITYTYPE_PHONECALL).count()),
             (_(u"Tasks count"),       act_filter(type=ACTIVITYTYPE_TASK).count()),
            )

    return app_portal(request, 'activity', 'activities/portal.html', Activity,
                      stats, config_url=generate_portal_url('activities'),
                     )
