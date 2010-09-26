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

from datetime import datetime
from logging import debug

from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.utils.simplejson import JSONEncoder, JSONDecoder
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User

#from creme_core.models import * #bof ?
from creme_core.entities_access.functions_for_permissions import get_view_or_die
from creme_core.entities_access.filter_allowed_objects import filter_can_read_objects
from creme_core.entities_access.permissions import user_has_edit_permission_for_an_object

from activities.models import Activity
from activities.utils import get_last_day_of_a_month


@login_required
@get_view_or_die('activities')
def get_users_calendar(request, usernames):
    return render_to_response('activities/calendar.html',
                              {
                                'events_url':    "/activities/calendar/users_activities/%s" % ",".join(usernames),
                                'users':         User.objects.all().order_by('username'),
                                'current_users': User.objects.filter(username__in=usernames)
                              },
                              context_instance=RequestContext(request))

def getFormattedDictFromAnActivity(activity):
    return {
            "id" :          int(activity.pk),
            "title":        activity.get_title_for_calendar(),
            "start":        activity.start.isoformat(),
            "end":          activity.end.isoformat(),
            "url":          "/activities/activity/%s/popup" % activity.pk,
            "entity_color": "#%s" % (activity.type.color or "C1D9EC"),
            "allDay" :      activity.is_all_day
            }

@login_required
@get_view_or_die('activities')
def user_calendar(request):
#    return getUserCalendar(request, request.POST.get('username', request.user.username))
    return get_users_calendar(request, request.POST.getlist('user_selected') or [request.user.username])

@login_required
@get_view_or_die('activities')
def my_calendar(request):
    return get_users_calendar(request, request.user.username)

@login_required
@get_view_or_die('activities')
def get_users_activities(request, usernames):
    users = User.objects.filter(username__in=usernames.split(','))

    if request.GET.has_key("start"):
        try:
            start = datetime.fromtimestamp(float(request.GET['start']))
        except:
            start = datetime.now().replace(day=1)
    else:
        start = datetime.now().replace(day=1)

    if request.GET.has_key("end") :
        try:
            end = datetime.fromtimestamp(float(request.GET['end']))
        except:
            end = get_last_day_of_a_month(start)
    else:
        end = get_last_day_of_a_month(start)

    current_activities = Q(start__range=(start, end))
    overlap_activities = Q(end__gt=start)
    overlap_activities2 = Q(start__lt=end)
    user_activities = Q(user__in=users)

    #TODO: user__in=users twice ???? can be rewrite better....
    list_activities = Activity.objects.filter(user__in=users).filter(current_activities | overlap_activities & overlap_activities2)
    list_activities = list_activities.filter(user_activities & Q(is_deleted=False))
    list_activities = filter_can_read_objects(request, list_activities)

    return HttpResponse(JSONEncoder().encode([getFormattedDictFromAnActivity(activity) for activity in list_activities.all()]),
                        mimetype = "text/javascript")

@login_required
@get_view_or_die('activities')
def update_activity_date(request):
    POST_get = request.POST.get
    id_ = POST_get('id')
    start_timestamp = POST_get('start')
    end_timestamp = POST_get('end')
    try:
        is_all_day = JSONDecoder().decode(POST_get('allDay', 'null'))
    except ValueError:
        is_all_day = None

    if id_ is not None and start_timestamp is not None and end_timestamp is not None:
        activity = get_object_or_404(Activity, pk=id_)

        if not user_has_edit_permission_for_an_object(request, activity, 'activities'):
            return HttpResponse("forbidden", mimetype="text/javascript", status=403)

        try:
            activity.start = datetime.fromtimestamp(float(start_timestamp) / 1000)#Js gives us miliseconds
            activity.end   = datetime.fromtimestamp(float(end_timestamp) / 1000)
            if is_all_day is not None:
                activity.is_all_day = is_all_day
                activity.handle_all_day()
        except ValueError:
            return HttpResponse("error", mimetype="text/javascript", status=400)

        activity.save()

        return HttpResponse("success", mimetype="text/javascript")

    return HttpResponse("error", mimetype="text/javascript", status=400)
