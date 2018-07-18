# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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
from copy import copy
from datetime import datetime, timedelta
import logging
from json import dumps as jsondumps
# import warnings

from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.utils.timezone import now, make_naive, get_current_timezone
from django.utils.translation import ugettext as _

from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.models import EntityCredentials
from creme.creme_core.utils import get_from_POST_or_404, jsonify
from creme.creme_core.utils.dates import make_aware_dt
from creme.creme_core.views import decorators, generic

from creme.persons import get_contact_model

from .. import get_activity_model, constants
from ..forms import calendar as calendar_forms
from ..models import Calendar
from ..utils import get_last_day_of_a_month, check_activity_collisions


logger = logging.getLogger(__name__)
Activity = get_activity_model()


def _activity_2_dict(activity, user):
    "Returns a 'jsonifiable' dictionary"
    tz = get_current_timezone()
    start = make_naive(activity.start, tz)
    end   = make_naive(activity.end, tz)

    # TODO: hack to hide start time of floating time activities, only way to do that without change js calendar api
    is_all_day = activity.is_all_day or activity.floating_type == constants.FLOATING_TIME

    if start == end and not is_all_day:
        end += timedelta(seconds=1)

    calendar = activity.calendar  # NB: _get_one_activity_per_calendar() adds this 'attribute'

    return {
        'id':           activity.id,
        'title':        activity.get_title_for_calendar(),
        'start':        start.isoformat(),
        'end':          end.isoformat(),
        'url':          reverse('activities__view_activity_popup', args=(activity.id,)),
        'calendar_color': '#{}'.format(calendar.get_color),  # TODO: calendarColor ?
        'allDay':       is_all_day,
        'editable':     user.has_perm_to_change(activity),
        'calendar':     calendar.id,
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


# TODO: less query ?
def _get_one_activity_per_calendar(calendar_ids, activities):
    # act = []
    # for activity in activities:
    #     for calendar in activity.calendars.filter(id__in=calendar_ids):
    #         activity.calendar = calendar
    #         act.append(copy(activity))
    # return act
    for activity in activities:
        for calendar in activity.calendars.filter(id__in=calendar_ids):
            copied = copy(activity)
            copied.calendar = calendar
            yield copied


def _js_timestamp_to_datetime(timestamp):
    "@raise ValueError"
    return make_aware_dt(datetime.fromtimestamp(float(timestamp) / 1000))  # JS gives us milliseconds


def _filter_authorized_calendars(user, calendar_ids):
    return list(Calendar.objects.filter((Q(is_public=True) |
                                         Q(user=user)) &
                                         Q(id__in=[cal_id
                                                     for cal_id in calendar_ids
                                                       if cal_id.isdigit()
                                                  ]
                                          )
                                        )
                                .values_list('id', flat=True)
                )


@login_required
@permission_required('activities')
def user_calendar(request):
    user = request.user
    getlist = request.POST.getlist  # TODO: POST ??

    # We don't really need the default calendar but this line creates one when the user has no calendar.
    Calendar.get_user_default_calendar(user)

    selected_calendars = getlist('selected_calendars')
    if selected_calendars:
        selected_calendars = _filter_authorized_calendars(user, selected_calendars)

    calendar_ids = selected_calendars or [c.id for c in Calendar.get_user_calendars(user)]

    others_calendars = defaultdict(list)
    creme_calendars_by_user = defaultdict(list)

    calendars = Calendar.objects.exclude(user=user).filter(is_public=True)

    for calendar in calendars:
        cal_user = calendar.user
        filter_key = '{} {} {}'.format(
                            cal_user.username,
                            cal_user.first_name,
                            cal_user.last_name,
                        )
        cal_user.filter_key = filter_key
        others_calendars[cal_user].append(calendar)
        creme_calendars_by_user[filter_key].append({'name': calendar.name,
                                                    'id': calendar.id})

    floating_activities = Activity.objects.filter(floating_type=constants.FLOATING,
                                                  relations__type=constants.REL_OBJ_PART_2_ACTIVITY,
                                                  relations__object_entity=user.linked_contact.id,
                                                  is_deleted=False,
                                                 )

    for activity in floating_activities:
        activity.calendar = activity.calendars.get(user=user)

    return render(request, 'activities/calendar.html',
                  {'user_username':           user.username,
                   # 'events_url':              reverse('activities__calendars_activities', args=('',)),
                   'events_url':              reverse('activities__calendars_activities'),
                   'max_element_search':      constants.MAX_ELEMENT_SEARCH,
                   'my_calendars':            Calendar.objects.filter(user=user),
                   'others_calendars':        dict(others_calendars),
                   'n_others_calendars':      len(calendars),
                   'creme_calendars_by_user': jsondumps(creme_calendars_by_user),  # TODO: use '|jsonify' ?
                   'current_calendars':       [str(id) for id in calendar_ids],
                   'creation_perm':           user.has_perm(cperm(Activity)),
                   # TODO only floating activities assigned to logged user ??
                   'floating_activities':     floating_activities,
                  }
                 )


@login_required
@permission_required('activities')
@jsonify
# def get_users_activities(request, calendar_ids=None):
def get_users_activities(request):
    GET = request.GET

    # if calendar_ids is not None:
    #     warnings.warn('activities.views.calendar.get_users_activities(): '
    #                   'the URL argument "calendar_ids" is deprecated ; '
    #                   'use the GET parameter "calendar_id" instead.',
    #                   DeprecationWarning
    #                  )
    #
    #     calendar_ids = calendar_ids.split(',')
    # else:
    #     calendar_ids = GET.getlist('calendar_id')
    calendar_ids = GET.getlist('calendar_id')

    user = request.user
    contacts = list(get_contact_model().objects.exclude(is_user=None)
                                       .values_list('id', flat=True)
                   )  # NB: list() to avoid inner query
    users_cal_ids = _filter_authorized_calendars(user, calendar_ids)

    start = _get_datetime(GET, 'start', (lambda: now().replace(day=1)))
    end   = _get_datetime(GET, 'end',   (lambda: get_last_day_of_a_month(start)))

    # TODO: label when no calendar related to the participant of an indispo
    # TODO: better way than distinct() then multiply instances with queries (see _get_one_activity_per_calendar) ?
    activities = EntityCredentials.filter(
                        user,
                        Activity.objects.filter(is_deleted=False)
                                        .filter(Q(start__range=(start, end)) |
                                                Q(end__gt=start, start__lt=end)
                                               )
                                        .filter(Q(calendars__pk__in=users_cal_ids) |
                                                Q(type=constants.ACTIVITYTYPE_INDISPO,
                                                  relations__type=constants.REL_OBJ_PART_2_ACTIVITY,
                                                  relations__object_entity__in=contacts,
                                                 )
                                               ).distinct()
                    )

    return [_activity_2_dict(activity, user)
                for activity in _get_one_activity_per_calendar(calendar_ids, activities)
           ]


@login_required
@permission_required('activities')
@jsonify
@decorators.POST_only
def update_activity_date(request):
    POST = request.POST

    act_id          = POST['id']
    start_timestamp = POST['start']
    end_timestamp   = POST['end']
    is_all_day      = POST.get('allDay')

    is_all_day = is_all_day.lower() in {'1', 'true'} if is_all_day else False

    activity = Activity.objects.get(pk=act_id)
    request.user.has_perm_to_change_or_die(activity)

    # This view is used when drag and dropping event comming from calendar
    # or external events (floating events).
    # Dropping a floating event on the calendar fixes it.
    if activity.floating_type == constants.FLOATING:
        activity.floating_type = constants.NARROW

    # TODO: factorise (_time_from_JS() function ??)
    activity.start = _js_timestamp_to_datetime(start_timestamp)
    activity.end   = _js_timestamp_to_datetime(end_timestamp)

    if is_all_day is not None and activity.floating_type != constants.FLOATING_TIME:
        activity.is_all_day = is_all_day
        activity.handle_all_day()

    collisions = check_activity_collisions(
                        activity.start, activity.end,
                        participants=[r.object_entity for r in activity.get_participant_relations()],
                        busy=activity.busy,
                        exclude_activity_id=activity.id,
                    )

    if collisions:
        raise ConflictError(u', '.join(collisions))  # TODO: improve msg ??

    activity.save()


@login_required
@permission_required('activities')
def add_user_calendar(request):
    return generic.add_model_with_popup(request, calendar_forms.CalendarForm, title=_(u'Create a calendar'),
                                        # initial={'color': Calendar.new_color()},
                                        submit_label=_('Save the calendar'),
                                       )


@login_required
@permission_required('activities')
def edit_user_calendar(request, calendar_id):
    return generic.edit_model_with_popup(request, query_dict={'pk': calendar_id},
                                         model=Calendar, form_class=calendar_forms.CalendarForm,
                                         can_change=lambda calendar, user: calendar.user == user,  # TODO: and superuser ??
                                        )


@login_required
@permission_required('activities')
@jsonify
def delete_user_calendar(request):
    # TODO: Adding the possibility to transfer activities
    calendar = get_object_or_404(Calendar, pk=get_from_POST_or_404(request.POST, 'id'))
    user = request.user

    # TODO: factorise calendar credentials functions ?
    if not calendar.is_custom or (not user.is_superuser and calendar.user_id != user.id):
        raise PermissionDenied(_(u'You are not allowed to delete this calendar.'))

    # Attach all existing activities to the default calendar
    default_calendar = Calendar.get_user_default_calendar(user)
    for activity in calendar.activity_set.all():
        activity.calendars.add(default_calendar)

    calendar.delete()


@login_required
@permission_required('activities')
def link_user_calendar(request, activity_id):
    return generic.edit_model_with_popup(request, query_dict={'pk': activity_id},
                                         model=Activity, form_class=calendar_forms.ActivityCalendarLinkerForm,
                                         title_format=_(u'Change calendar of «%s»'),
                                         # can_change=lambda activity, user: user.has_perm_to_link(activity),
                                         can_change=lambda activity, user: True,
                                        )
