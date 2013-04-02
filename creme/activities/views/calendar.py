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

from datetime import datetime, timedelta
#from logging import debug

from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.utils.simplejson import JSONEncoder, JSONDecoder
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User

from creme.creme_core.models import EntityCredentials
from creme.creme_core.views.generic import add_model_with_popup, edit_model_with_popup
from creme.creme_core.utils import get_from_POST_or_404

from ..models import Activity, Calendar
from ..utils import get_last_day_of_a_month, check_activity_collisions
from ..forms.calendar import CalendarForm
from ..constants import ACTIVITYTYPE_INDISPO


@login_required
@permission_required('activities')
def get_users_calendar(request, usernames, calendars_ids):
    user = request.user
    if user.username not in usernames:
        calendars_ids = []

    cal_ids = [str(id) for id in calendars_ids]
    return render(request, 'activities/calendar.html',
                  {'events_url':        "/activities/calendar/users_activities/%s/%s" % (",".join(usernames), ",".join(cal_ids)),
                   'users':             User.objects.order_by('username'),
                   'current_users':     User.objects.filter(username__in=usernames), #TODO: avoid this query by filter in python...
                   'my_calendars' :     Calendar.objects.filter(user=user),
                   'current_calendars': cal_ids,
                   'creation_perm':     user.has_perm('activities.add_activity'),
                  }
                 )

#TODO: rename
def getFormattedDictFromAnActivity(activity, user):
    start = activity.start
    end   = activity.end
    is_all_day = activity.is_all_day

    if start == end and not is_all_day:
        end += timedelta(seconds=1)

    is_editable = activity.can_change(user) #TODO: inline

    return {"id" :          int(activity.pk),
            "title":        activity.get_title_for_calendar(),
            "start":        start.isoformat(),
            "end":          end.isoformat(),
            "url":          "/activities/activity/%s/popup" % activity.pk,
            "entity_color": "#%s" % (activity.type.color or "C1D9EC"),
            "allDay" :      is_all_day,
            "editable":     is_editable,
           }

@login_required
@permission_required('activities')
def user_calendar(request):
#    return getUserCalendar(request, request.POST.get('username', request.user.username))
    user = request.user
    getlist = request.POST.getlist
    Calendar.get_user_default_calendar(user)#Don't really need the calendar but this create it in case of the user hasn't a calendar

    #usernames = User.objects.values_list('username', flat=True)

    #TODO: useful to compute if getlist('calendar_selected') is not empty ??
    calendars_ids = Calendar.get_user_calendars(user, False).values_list('id', flat=True)
    if not calendars_ids:
        calendars_ids = [Calendar.get_user_default_calendar(user).pk]

    return get_users_calendar(request,
                              getlist('user_selected') or [user.username],#usernames,
                              getlist('calendar_selected') or calendars_ids#[Calendar.get_user_default_calendar(user).pk])
                             )

def my_calendar(request):
    user = request.user
    return get_users_calendar(request, user.username, [Calendar.get_user_default_calendar(user).pk])

#TODO: need refactoring (and certainly unit tests...)
@login_required
@permission_required('activities')
def get_users_activities(request, usernames, calendars_ids):
    users = User.objects.filter(username__in=usernames.split(',')) #TODO: problem => this queryset causes nested queries later
    GET = request.GET

    #TODO: list comprehesion + isdigit()
    cals_ids = []
    for cal_id in calendars_ids.split(','):
        if cal_id:
            try:
                cals_ids.append(long(cal_id))
            except ValueError:
                continue

    #TODO: user = request.user
    #TODO: use exclude() ...
    #TODO: exclude request.user from seque,ce in python, to avoid a query
    users_cal_ids  = set(Calendar.objects.filter(is_public=True, user__in=users.filter(~Q(pk=request.user.pk))).values_list('id', flat=True))
    users_cal_ids |= set(cals_ids)

    if GET.has_key("start"):
        try:
            start = datetime.fromtimestamp(float(GET['start']))
        except:
            start = datetime.now().replace(day=1)
    else:
        start = datetime.now().replace(day=1) #TODO: factorise (with smart exception usage....)

    if GET.has_key("end"):
        try:
            end = datetime.fromtimestamp(float(GET['end']))
        except:
            end = get_last_day_of_a_month(start)
    else:
        end = get_last_day_of_a_month(start)

    activities = EntityCredentials.filter(
                        request.user,
                        Activity.objects.filter(is_deleted=False)
                                        .filter(Q(start__range=(start, end)) |
                                                Q(end__gt=start, start__lt=end)
                                               )
                                        .filter(Q(calendars__pk__in=users_cal_ids) |
                                                Q(type=ACTIVITYTYPE_INDISPO, user__in=users)
                                               )
                    )

    return HttpResponse(JSONEncoder().encode([getFormattedDictFromAnActivity(activity, request.user) for activity in activities]),
                        mimetype="text/javascript"
                       )

@login_required
@permission_required('activities')
def update_activity_date(request):
    POST_get = request.POST.get
    id_             = POST_get('id')
    start_timestamp = POST_get('start')
    end_timestamp   = POST_get('end')

    try:
        is_all_day = JSONDecoder().decode(POST_get('allDay', 'null'))
    except ValueError:
        is_all_day = None

    if id_ is not None and start_timestamp is not None and end_timestamp is not None: #TODO: use a guard instead ??
        activity = get_object_or_404(Activity, pk=id_)

        #if not user_has_edit_permission_for_an_object(request, activity, 'activities'):
        if not activity.can_change(request.user):
            return HttpResponse("forbidden", mimetype="text/javascript", status=403)

        try:
            #TODO:factorise (_time_from_JS() function ??)
            activity.start = datetime.fromtimestamp(float(start_timestamp) / 1000)#Js gives us miliseconds
            activity.end   = datetime.fromtimestamp(float(end_timestamp) / 1000)
            if is_all_day is not None:
                activity.is_all_day = is_all_day
                activity.handle_all_day()
        except ValueError:
            return HttpResponse("error", mimetype="text/javascript", status=400)

        participants = [act.object_entity for act in activity.get_participant_relations()]
        collisions = check_activity_collisions(activity.start, activity.end, participants, busy=activity.busy, exclude_activity_id=activity.id)
        if collisions:
            return HttpResponse(u", ".join(collisions), mimetype="text/plain", status=409)

        activity.save()

        return HttpResponse("success", mimetype="text/javascript")

    return HttpResponse("error", mimetype="text/javascript", status=400)

@login_required
@permission_required('activities')
def add_user_calendar(request):
    return add_model_with_popup(request, CalendarForm, title=_(u'Add a calendar'))

@login_required
@permission_required('activities')
def edit_user_calendar(request, calendar_id):
    return edit_model_with_popup(request, query_dict={'pk': calendar_id},
                                 model=Calendar, form_class=CalendarForm,
                                 can_change=lambda calendar, user: calendar.user == user, #TODO: and superuser ??
                                )

@login_required
@permission_required('activities')
def delete_user_calendar(request):
    #TODO: Adding the possibility to transfert activities
    calendar = get_object_or_404(Calendar, pk=get_from_POST_or_404(request.POST, 'id'))
    status, msg = 200, ""
    user = request.user

    #TODO: simply raise PermissionDenied ?
    #TODO: factorise calendar credentials functions ?
    if (user.is_superuser or calendar.user == user) and calendar.is_custom:
        calendar.delete()
    else:
        status = 403
        msg = _(u"You are not allowed to delete this calendar.")

    return HttpResponse(msg, mimetype="text/javascript", status=status)
