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

from collections import defaultdict
import copy
from datetime import datetime, timedelta
import logging

from django.core.exceptions import PermissionDenied
from django.db.models import Q
#from django.http import Http404 HttpResponse
from django.shortcuts import render, get_object_or_404
#from django.utils.simplejson import JSONDecoder JSONEncoder
from django.utils.simplejson import loads as jsonloads, dumps as jsondumps
from django.utils.timezone import now, make_naive, get_current_timezone
from django.utils.translation import ugettext as _
# from django.contrib.auth.models import User

from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.models import EntityCredentials
from creme.creme_core.utils import get_from_POST_or_404, jsonify
from creme.creme_core.utils.dates import make_aware_dt
from creme.creme_core.views.decorators import POST_only
from creme.creme_core.views.generic import add_model_with_popup, edit_model_with_popup #inner_popup

from creme.persons.models import Contact

from ..models import Activity, Calendar
from ..utils import get_last_day_of_a_month, check_activity_collisions
from ..forms.calendar import CalendarForm, ActivityCalendarLinkerForm
from ..constants import (FLOATING, FLOATING_TIME, ACTIVITYTYPE_INDISPO,
        REL_OBJ_PART_2_ACTIVITY, DEFAULT_CALENDAR_COLOR, NARROW, MAX_ELEMENT_SEARCH)


logger = logging.getLogger(__name__)


def _activity_2_dict(activity, user):
    "Return a 'jsonifiable' dictionary"
    #start = activity.start
    #end   = activity.end
    tz = get_current_timezone()
    start = make_naive(activity.start, tz)
    end   = make_naive(activity.end, tz)

    #TODO: hack to hide start time of floating time activities, only way to do that without change js calendar api
    is_all_day = activity.is_all_day or activity.floating_type == FLOATING_TIME

    if start == end and not is_all_day:
        end += timedelta(seconds=1)

    return {'id' :          int(activity.pk), #TODO: int() useful ??
            'title':        activity.get_title_for_calendar(),
            'start':        start.isoformat(),
            'end':          end.isoformat(),
            'url':          "/activities/activity/%s/popup" % activity.pk,
            'calendar_color': "#%s" % (activity.calendar.get_color or DEFAULT_CALENDAR_COLOR),
            'allDay' :      is_all_day,
            'editable':     user.has_perm_to_change(activity),
            'calendar':     activity.calendar.id,
            'type':         activity.type.name,
           }

def _get_datetime(data, key, default_func):
    timestamp = data.get(key)
    if timestamp is not None:
        try:
            return make_aware_dt(datetime.fromtimestamp(float(timestamp)))
        except Exception:
            logger.exception('_get_datetime(key=%s)', key)

    return default_func()

def _get_one_activity_per_calendar(calendar_ids, activities):
    act = []
    for activity in activities:
        for calendar in activity.calendars.filter(id__in=calendar_ids):
            activity.calendar = calendar
            act.append(copy.copy(activity))
    return act

def _js_timestamp_to_datetime(timestamp):
    "@raise ValueError"
    #return datetime.fromtimestamp(float(timestamp) / 1000) #Js gives us miliseconds
    return make_aware_dt(datetime.fromtimestamp(float(timestamp) / 1000)) #Js gives us miliseconds

def _filter_authorized_calendars(user, calendar_ids):
    return list(Calendar.objects.filter((Q(is_public=True) |
                                         Q(user=user)) &
                                         Q(id__in=[cal_id
                                                   for cal_id in calendar_ids
                                                   if cal_id.isdigit()
                                                  ]
                                          )).values_list('id', flat=True))


@login_required
@permission_required('activities')
def user_calendar(request):
    user = request.user
    getlist = request.POST.getlist #TODO: POST ??
    Calendar.get_user_default_calendar(user)#Don't really need the calendar but this create it in case of the user hasn't a calendar

    selected_calendars = getlist('selected_calendars')
    if selected_calendars:
        selected_calendars = _filter_authorized_calendars(user, selected_calendars)

    calendar_ids = selected_calendars or [c.id for c in Calendar.get_user_calendars(user)]

    others_calendars = defaultdict(list)
    creme_calendars_by_user = defaultdict(list)

    calendars = Calendar.objects.exclude(user=user).filter(is_public=True)

    for calendar in calendars:
        cal_user = calendar.user
        filter_key = "%s %s %s" % (cal_user.username,
                                   cal_user.first_name,
                                   cal_user.last_name)
        cal_user.filter_key = filter_key
        others_calendars[cal_user].append(calendar)
        creme_calendars_by_user[filter_key].append({'name': calendar.name,
                                                    'id': calendar.id})

    floating_activities = Activity.objects.filter(floating_type=FLOATING,
                                                  relations__type=REL_OBJ_PART_2_ACTIVITY,
                                                  relations__object_entity=Contact.get_user_contact_or_mock(user).id,
                                                  is_deleted=False,
                                                  )

    for activity in floating_activities:
        activity.calendar = activity.calendars.get(user=user)

    return render(request, 'activities/calendar.html',
                  {'user_username':           user.username,
                   'events_url':              '/activities/calendar/users_activities/',
                   # 'users':                   User.objects.order_by('username'),
                   'max_element_search':      MAX_ELEMENT_SEARCH,
                   'my_calendars':            Calendar.objects.filter(user=user),
                   'others_calendars':        dict(others_calendars),
                   'n_others_calendars':      len(calendars),
                   'creme_calendars_by_user': jsondumps(creme_calendars_by_user),
                   'current_calendars':       [str(id) for id in calendar_ids],
                   'creation_perm':           user.has_perm('activities.add_activity'),
                   'floating_activities':     floating_activities, #TODO only floating activities assigned to logged user ??
                  }
                 )

@login_required
@permission_required('activities')
@jsonify
def get_users_activities(request, calendar_ids):
    user = request.user
    calendar_ids = calendar_ids.split(',')
    # users    = list(User.objects.filter(username__in=usernames.split(','))) #NB: list() to avoid inner query
    contacts = list(Contact.objects.exclude(is_user=None).values_list('id', flat=True)) #idem

    users_cal_ids = _filter_authorized_calendars(user, calendar_ids)

    GET = request.GET
    start = _get_datetime(GET, 'start', (lambda: now().replace(day=1)))
    end   = _get_datetime(GET, 'end',   (lambda: get_last_day_of_a_month(start)))

    #TODO: label when no calendar related to the participant of an indispo
    activities = EntityCredentials.filter(
                        user,
                        Activity.objects.filter(is_deleted=False)
                                        .filter(Q(start__range=(start, end)) |
                                                Q(end__gt=start, start__lt=end)
                                               )
                                        .filter(Q(calendars__pk__in=users_cal_ids) |
                                                Q(type=ACTIVITYTYPE_INDISPO, #user__in=users
                                                  relations__type=REL_OBJ_PART_2_ACTIVITY,
                                                  relations__object_entity__in=contacts,
                                                 )
                                               ).distinct()
                    )

    #return HttpResponse(JSONEncoder().encode([_activity_2_dict(activity, user)
                                                #for activity in activities
                                             #]
                                            #),
                        #mimetype='text/javascript'
                       #)
    return [_activity_2_dict(activity, user) for activity in _get_one_activity_per_calendar(calendar_ids, activities)]

@login_required
@permission_required('activities')
@jsonify
@POST_only
def update_activity_date(request):
    POST = request.POST

    act_id          = POST['id']
    start_timestamp = POST['start']
    end_timestamp   = POST['end']
    is_all_day = POST.get('allDay')

    if is_all_day is not None:
        is_all_day = bool(jsonloads(is_all_day))

    activity = Activity.objects.get(pk=act_id)
    request.user.has_perm_to_change_or_die(activity)

    #This view is used when drag and dropping event comming from calendar
    #or external events (floating events).
    #Dropping a floating event on the calendar fixes it.
    if activity.floating_type == FLOATING:
        activity.floating_type = NARROW

    #TODO: factorise (_time_from_JS() function ??)
    activity.start = _js_timestamp_to_datetime(start_timestamp)
    activity.end   = _js_timestamp_to_datetime(end_timestamp)

    if is_all_day is not None and activity.floating_type != FLOATING_TIME:
        activity.is_all_day = is_all_day
        activity.handle_all_day()

    collisions = check_activity_collisions(
                        activity.start, activity.end,
                        participants=[r.object_entity for r in activity.get_participant_relations()],
                        busy=activity.busy,
                        exclude_activity_id=activity.id,
                    )

    if collisions:
        raise ConflictError(u', '.join(collisions)) #TODO: improve msg ??

    activity.save()

@login_required
@permission_required('activities')
def add_user_calendar(request):
    return add_model_with_popup(request, CalendarForm, title=_(u'Add a calendar'),
                                initial={'color': Calendar.new_color()})

@login_required
@permission_required('activities')
def edit_user_calendar(request, calendar_id):
    return edit_model_with_popup(request, query_dict={'pk': calendar_id},
                                 model=Calendar, form_class=CalendarForm,
                                 can_change=lambda calendar, user: calendar.user == user, #TODO: and superuser ??
                                )

@login_required
@permission_required('activities')
@jsonify
def delete_user_calendar(request):
    #TODO: Adding the possibility to transfert activities
    calendar = get_object_or_404(Calendar, pk=get_from_POST_or_404(request.POST, 'id'))
    user = request.user

    #TODO: factorise calendar credentials functions ?
    if not calendar.is_custom or (not user.is_superuser and calendar.user_id != user.id):
        raise PermissionDenied(_(u'You are not allowed to delete this calendar.'))

    # Attach all existing activities to default calendar
    default_calendar = Calendar.get_user_default_calendar(user)
    for activity in calendar.activity_set.all():
        activity.calendars.add(default_calendar)

    calendar.delete()

@login_required
@permission_required('activities')
def link_user_calendar(request, activity_id):
    return edit_model_with_popup(request, query_dict={'pk': activity_id},
                                 model=Activity, form_class=ActivityCalendarLinkerForm,
                                 title_format=_(u"Change calendar of <%s>"),
                                 #can_change=lambda activity, user: user.has_perm_to_link(activity),
                                 can_change=lambda activity, user: True,
                                )

    ##We cannot use the generic view add_to_entity because we need to reload after posting.
    #user = request.user
    #activity = get_object_or_404(Activity, pk=activity_id)

    #user.has_perm_to_link_or_die(activity)

    #if request.method == 'POST':
        #form = ActivityCalendarLinkerForm(activity,
                                          #user=user,
                                          #data=request.POST,
                                          #files=request.FILES or None)

        #if form.is_valid():
            #form.save()
    #else:
        #form = ActivityCalendarLinkerForm(activity, user=user)

    #return inner_popup(request, 'creme_core/generics/blockform/add_popup2.html',
                       #{'form':  form,
                        ##'title': _(u"Add on a calendar"),
                        #'title': _(u"Change calendar"),
                       #},
                       #is_valid=form.is_valid(),
                       #reload=True,
                       #delegate_reload=True,
                      #)
