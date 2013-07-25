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
import logging

from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import Http404 #HttpResponse
from django.shortcuts import render, get_object_or_404
from django.utils.simplejson import JSONDecoder #JSONEncoder
from django.utils.timezone import now, make_naive, get_current_timezone
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User

from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.models import EntityCredentials
from creme.creme_core.views.generic import add_model_with_popup, edit_model_with_popup
from creme.creme_core.utils import get_from_POST_or_404, jsonify
from creme.creme_core.utils.dates import make_aware_dt

from creme.persons.models import Contact

from ..models import Activity, Calendar
from ..utils import get_last_day_of_a_month, check_activity_collisions
from ..forms.calendar import CalendarForm
from ..constants import FLOATING, FLOATING_TIME, ACTIVITYTYPE_INDISPO, REL_OBJ_PART_2_ACTIVITY


logger = logging.getLogger(__name__)


def _get_users_calendar(request, usernames, calendars_ids): #TODO: used once ??
    user = request.user
    usernames = frozenset(usernames)

    if user.username not in usernames:
        calendars_ids = []

    cal_ids = [str(id) for id in calendars_ids]
    users = User.objects.order_by('username')

    return render(request, 'activities/calendar.html',
                  {'events_url':          '/activities/calendar/users_activities/%s/%s' % (
                                                    ','.join(usernames),
                                                    ','.join(cal_ids),
                                                ),
                   'users':               users,
                   'current_users':       [u for u in users if u.username in usernames],
                   'my_calendars' :       Calendar.objects.filter(user=user),
                   'current_calendars':   cal_ids,
                   'creation_perm':       user.has_perm('activities.add_activity'),
                   'floating_activities': Activity.objects.filter(user=user,
                                                                  floating_type=FLOATING,
                                                                  is_deleted=False,
                                                                 ), #TODO only floating activities assigned to logged user ??
                  }
                 )

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
            'entity_color': "#%s" % (activity.type.color or 'C1D9EC'),
            'allDay' :      is_all_day,
            'editable':     user.has_perm_to_change(activity),
           }

@login_required
@permission_required('activities')
def user_calendar(request):
    user = request.user
    getlist = request.POST.getlist #TODO: POST ??
    Calendar.get_user_default_calendar(user)#Don't really need the calendar but this create it in case of the user hasn't a calendar

    return _get_users_calendar(request,
                               getlist('user_selected') or [user.username],
                               #getlist('calendar_selected') or Calendar.get_user_calendars(user)
                                                                       #.values_list('id', flat=True),
                               getlist('calendar_selected') or [c.id for c in Calendar.get_user_calendars(user)],
                              )

#COMMENTED on march 2013
#@login_required
#@permission_required('activities')
#def my_calendar(request):
    #user = request.user
    #return _get_users_calendar(request, user.username,
                               #[Calendar.get_user_default_calendar(user).pk]
                              #)

def _get_datetime(data, key, default_func):
    timestamp = data.get(key)

    if timestamp is not None:
        try:
            #return datetime.fromtimestamp(float(timestamp))
            return make_aware_dt(datetime.fromtimestamp(float(timestamp)))
        except Exception:
            logger.exception('_get_datetime(key=%s)', key)

    return default_func()

@login_required
@permission_required('activities')
@jsonify
def get_users_activities(request, usernames, calendars_ids):
    user = request.user

    users    = list(User.objects.filter(username__in=usernames.split(','))) #NB: list() to avoid inner query
    contacts = list(Contact.objects.filter(is_user__in=users).values_list('id', flat=True)) #idem

    users_cal_ids = list(Calendar.objects
                                 .filter(Q(is_public=True) |
                                         Q(user=user,
                                           id__in=[cal_id
                                                       for cal_id in calendars_ids.split(',')
                                                         if cal_id.isdigit()
                                                  ]
                                          )
                                        )
                                 .values_list('id', flat=True)
                        )

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
    return [_activity_2_dict(activity, user) for activity in activities]


def _js_timestamp_to_datetime(timestamp):
    "@raise ValueError"
    #return datetime.fromtimestamp(float(timestamp) / 1000) #Js gives us miliseconds
    return make_aware_dt(datetime.fromtimestamp(float(timestamp) / 1000)) #Js gives us miliseconds

@login_required
@permission_required('activities')
@jsonify
def update_activity_date(request):
    if request.method != 'POST':
        raise Http404

    POST = request.POST

    act_id          = POST['id']
    start_timestamp = POST['start']
    end_timestamp   = POST['end']

    #try:
        #is_all_day = JSONDecoder().decode(POST.get('allDay', 'null'))
    #except ValueError as e:
        #logger.debug('update_activity_date(): %s', e)
        #is_all_day = None
    is_all_day = POST.get('allDay')

    if is_all_day is not None:
        is_all_day = bool(JSONDecoder().decode(is_all_day))

    activity = Activity.objects.get(pk=act_id)
    request.user.has_perm_to_change_or_die(activity)

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
@jsonify
def delete_user_calendar(request):
    #TODO: Adding the possibility to transfert activities
    calendar = get_object_or_404(Calendar, pk=get_from_POST_or_404(request.POST, 'id'))
    user = request.user

    #TODO: factorise calendar credentials functions ?
    if not calendar.is_custom or (not user.is_superuser and calendar.user_id != user.id):
        raise PermissionDenied(_(u'You are not allowed to delete this calendar.'))

    calendar.delete()
