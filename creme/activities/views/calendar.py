# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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

import logging
from collections import defaultdict
from copy import copy
from datetime import datetime, timedelta
from functools import partial

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.db.models import Prefetch, Q
from django.db.transaction import atomic
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.timezone import get_current_timezone, make_naive, now
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.http import CremeJsonResponse
from creme.creme_core.models import DeletionCommand, EntityCredentials, Job
from creme.creme_core.utils import bool_from_str_extended, get_from_POST_or_404
from creme.creme_core.utils.dates import make_aware_dt
from creme.creme_core.utils.unicode_collation import collator
from creme.creme_core.views import generic

from .. import constants, get_activity_model
from ..forms import calendar as calendar_forms
from ..models import Calendar
from ..utils import check_activity_collisions, get_last_day_of_a_month

logger = logging.getLogger(__name__)
Activity = get_activity_model()


def _js_timestamp_to_datetime(timestamp):
    "@raise ValueError"
    # JS gives us milliseconds
    return make_aware_dt(datetime.fromtimestamp(float(timestamp) / 1000))


class CalendarView(generic.CheckedTemplateView):
    template_name = 'activities/calendar.html'
    permissions = 'activities'

    calendar_id_arg = 'calendar_id'
    calendars_search_threshold = 10
    floating_activities_search_threshold = 10

    calendar_ids_session_key = 'activities__calendars'

    @staticmethod
    def _filter_default_calendars(user, calendars):
        user_id = user.id
        for calendar in calendars:
            if calendar.user_id == user_id and calendar.is_default:
                yield calendar

    def get_floating_activities(self):
        # TODO only floating activities assigned to logged user ??
        floating_activities = []
        user = self.request.user

        for activity in Activity.objects.filter(
            floating_type=constants.FLOATING,
            relations__type=constants.REL_OBJ_PART_2_ACTIVITY,
            relations__object_entity=user.linked_contact.id,
            is_deleted=False,
        ):
            try:
                activity.calendar = activity.calendars.get(user=user)
            except Calendar.DoesNotExist:
                pass
            else:
                floating_activities.append(activity)

        return floating_activities

    def get_selected_calendar_ids(self, calendars):
        request = self.request
        request_calendar_ids = request.GET.getlist(self.calendar_id_arg)

        if request_calendar_ids:
            # TODO: error (message VS exception) if not int ?
            raw_ids = {int(cal_id) for cal_id in request_calendar_ids if cal_id.isdigit()}
        else:
            raw_ids = {*request.session.get(self.calendar_ids_session_key, ())}

        return [
            calendar.id for calendar in calendars if calendar.id in raw_ids
        ]

    def get_calendars(self, user):
        # NB: we retrieve all the user's Calendars to check the presence of the
        #     default one (& create it if needed) by avoiding an extra query.
        calendars = [*Calendar.objects.filter(
            Q(user=user)
            | Q(is_public=True, user__is_staff=False, user__is_active=True)
        )]

        if next(self._filter_default_calendars(user, calendars), None) is None:
            calendars.append(Calendar.objects.create_default_calendar(
                user=user,
                is_public=bool(settings.ACTIVITIES_DEFAULT_CALENDAR_IS_PUBLIC),
            ))

        return calendars

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        calendars = self.get_calendars(user)
        # TODO: populate 'user' ?

        my_calendars = []
        others_calendars = defaultdict(list)
        others_calendar_ids = []

        for calendar in calendars:
            cal_user = calendar.user

            if cal_user == user:
                my_calendars.append(calendar)
            else:
                others_calendars[cal_user].append(calendar)
                others_calendar_ids.append(calendar.id)

        context['my_calendars'] = my_calendars

        sort_key = collator.sort_key
        other_users = [*others_calendars.keys()]
        other_users.sort(key=lambda u: sort_key(str(u)))
        context['others_calendars'] = [(u, others_calendars[u]) for u in other_users]

        selected_calendars_ids = set(
            self.get_selected_calendar_ids(calendars)
            or (
                calendar.id
                for calendar in self._filter_default_calendars(user, calendars)
            )
        )
        context['my_selected_calendar_ids'] = {
            cal.id for cal in my_calendars if cal.id in selected_calendars_ids
        }
        context['others_selected_calendar_ids'] = {
            cal_id for cal_id in others_calendar_ids if cal_id in selected_calendars_ids
        }

        context['enable_calendars_search'] = (
            len(calendars) >= self.calendars_search_threshold
        )  # TODO: unit test for <True> case

        context['floating_activities'] = f_activities = self.get_floating_activities()
        context['enable_floating_activities_search'] = (
            len(f_activities) >= self.floating_activities_search_threshold
        )  # TODO: unit test for <True> case

        return context


class CalendarsMixin:
    calendar_id_arg = 'calendar_id'

    @staticmethod
    def _str_ids_2_int_ids(str_ids):
        for str_id in str_ids:
            if str_id.isdigit():
                yield int(str_id)

    def get_calendar_raw_ids(self, request):
        return request.GET.getlist(self.calendar_id_arg)

    def get_calendars(self, request):
        calendar_ids = [*self._str_ids_2_int_ids(self.get_calendar_raw_ids(request))]

        return Calendar.objects.filter(
            (Q(is_public=True) | Q(user=request.user)) & Q(id__in=calendar_ids)
        ) if calendar_ids else Calendar.objects.none()


class ActivitiesData(CalendarsMixin, generic.CheckedView):
    response_class = CremeJsonResponse
    start_arg = 'start'
    end_arg = 'end'

    # Example of possible format (NB: "activity" is passed in the context)
    # label = '[{activity.status}] {activity.title}'
    label = '{activity.title}'
    calendar_ids_session_key = CalendarView.calendar_ids_session_key

    def get(self, request, *args, **kwargs):
        return self.response_class(
            self.get_activities_data(request),
            safe=False,  # Result is not a dictionary
        )

    def get_activity_label(self, activity):
        return self.label.format(activity=activity)

    # @staticmethod
    # def _activity_2_dict(activity, user):
    def _activity_2_dict(self, activity, user):
        "Returns a 'jsonifiable' dictionary."
        tz = get_current_timezone()
        start = make_naive(activity.start, tz)
        end = make_naive(activity.end, tz)

        if activity.is_all_day:
            end = datetime(year=end.year, month=end.month, day=end.day) + timedelta(days=1)

        # NB: _get_one_activity_per_calendar() adds this 'attribute'
        calendar = activity.calendar

        return {
            'id':    activity.id,
            # 'title': activity.title,
            'title': self.get_activity_label(activity),

            'start':  start.isoformat(),
            'end':    end.isoformat(),
            'allDay': activity.is_all_day,

            'url': reverse('activities__view_activity_popup', args=(activity.id,)),

            'color':    f'#{calendar.get_color}',
            'editable': user.has_perm_to_change(activity),
            'calendar': calendar.id,
            'type':     activity.type.name,
        }

    @staticmethod
    def _get_datetime(*, request, key):
        timestamp = request.GET.get(key)

        if timestamp is not None:
            try:
                return make_aware_dt(datetime.fromtimestamp(float(timestamp)))
            except Exception:
                logger.exception('ActivitiesData._get_datetime(key=%s)', key)

    @staticmethod
    def _get_one_activity_per_calendar(activities):
        for activity in activities:
            # "concerned_calendars" is added by get_activities_data()
            for calendar in activity.concerned_calendars:
                copied = copy(activity)
                copied.calendar = calendar
                yield copied

    def get_activities_data(self, request):
        user = request.user

        calendar_ids = [cal.id for cal in self.get_calendars(request)]
        self.save_calendar_ids(request, calendar_ids)

        start = self.get_start(request)
        end   = self.get_end(request=request, start=start)

        # TODO: label when no calendar related to the participant of an unavailability
        activities = EntityCredentials.filter(
            user,
            Activity.objects
                    .filter(is_deleted=False)
                    .filter(self.get_date_q(start=start, end=end))
                    .filter(calendars__in=calendar_ids)
                    .distinct()
            # NB: we already filter by calendars ; maybe a future Django version
            #     will allow us to annotate the calendar ID directly
            #     (distinct() would have to be removed of course)
                    .prefetch_related(Prefetch(
                        'calendars',
                        queryset=Calendar.objects.filter(id__in=calendar_ids),
                        to_attr='concerned_calendars',
                    ))
        )

        activity_2_dict = partial(self._activity_2_dict, user=user)

        return [
            activity_2_dict(activity=a)
            for a in self._get_one_activity_per_calendar(activities)
        ]

    @staticmethod
    def get_date_q(start, end):
        return Q(start__range=(start, end)) | Q(end__gt=start, start__lt=end)

    def get_end(self, request, start):
        return (
            self._get_datetime(request=request, key=self.end_arg)
            or get_last_day_of_a_month(start)
        )

    def get_start(self, request):
        return (
            self._get_datetime(request=request, key=self.start_arg)
            or now().replace(day=1)
        )

    def save_calendar_ids(self, request, calendar_ids):
        # TODO: GET argument to avoid saving ?
        key = self.calendar_ids_session_key
        session = request.session

        if calendar_ids != session.get(key):
            session[key] = calendar_ids


class CalendarsSelection(CalendarsMixin, generic.CheckedView):
    """View which can add & remove selected calendar IDs in the session.
    It's mostly useful to remove IDs without retrieving Activities data
    (see ActivitiesData) ; the <add> command is here to get a more
    consistent/powerful API.
    """
    add_arg = 'add'
    remove_arg = 'remove'
    calendar_ids_session_key = CalendarView.calendar_ids_session_key

    def get_calendar_raw_ids(self, request):
        return request.POST.getlist(self.add_arg)

    def post(self, request, *args, **kwargs):
        session = request.session
        key = self.calendar_ids_session_key

        calendar_ids = set(session.get(key) or ())
        calendar_ids.update(cal.id for cal in self.get_calendars(request))
        ids_2remove = {*self._str_ids_2_int_ids(request.POST.getlist(self.remove_arg))}

        session[key] = [
            cal_id for cal_id in calendar_ids if cal_id not in ids_2remove
        ]

        return HttpResponse()


class ActivityDatesSetting(generic.base.EntityRelatedMixin, generic.CheckedView):
    """This view is used when drag & dropping Activities in the Calendar."""
    permissions = 'activities'
    entity_classes = Activity
    entity_select_for_update = True

    activity_id_arg = 'id'
    start_arg = 'start'
    end_arg = 'end'
    all_day_arg = 'allDay'

    def get_related_entity_id(self):
        return get_from_POST_or_404(self.request.POST, key=self.activity_id_arg, cast=int)

    @atomic
    def post(self, request, *args, **kwargs):
        POST = request.POST
        start = get_from_POST_or_404(
            POST, key=self.start_arg, cast=_js_timestamp_to_datetime,
        )
        end = get_from_POST_or_404(
            POST, key=self.end_arg, cast=_js_timestamp_to_datetime
        )
        is_all_day = get_from_POST_or_404(
            POST, key=self.all_day_arg,
            cast=bool_from_str_extended, default='false',
        )

        activity = self.get_related_entity()

        # Dropping a floating Activity on the Calendar fixes it.
        if activity.floating_type == constants.FLOATING:
            activity.floating_type = constants.NARROW

        activity.start = start
        activity.end = end
        activity.is_all_day = is_all_day

        activity.handle_all_day()

        collisions = check_activity_collisions(
            activity.start, activity.end,
            participants=[r.object_entity for r in activity.get_participant_relations()],
            busy=activity.busy,
            exclude_activity_id=activity.id,
        )

        if collisions:
            raise ConflictError(', '.join(collisions))  # TODO: improve message?

        activity.save()

        return HttpResponse()


class CalendarCreation(generic.CremeModelCreationPopup):
    model = Calendar
    form_class = calendar_forms.CalendarForm
    permissions = 'activities'


class CalendarEdition(generic.CremeModelEditionPopup):
    model = Calendar
    form_class = calendar_forms.CalendarForm
    permissions = 'activities'
    pk_url_kwarg = 'calendar_id'

    def check_instance_permissions(self, instance, user):
        if instance.user != user:  # TODO: and superuser ??
            raise PermissionDenied('You cannot edit this Calendar (it is not yours).')


class CalendarDeletion(generic.CremeModelEditionPopup):
    model = Calendar
    form_class = calendar_forms.CalendarDeletionForm
    permissions = 'activities'
    pk_url_kwarg = 'calendar_id'
    title = _('Replace & delete «{object}»')
    job_template_name = 'creme_config/deletion-job-popup.html'

    def check_instance_permissions(self, instance, user):
        if not instance.is_custom:
            raise ConflictError(
                gettext('You cannot delete this calendar: it is not custom.')
            )

        if instance.user_id != user.id:
            raise PermissionDenied(gettext('You are not allowed to delete this calendar.'))

        if not Calendar.objects.filter(user=user).exclude(id=instance.id).exists():
            raise ConflictError(gettext('You cannot delete your last calendar.'))

        ctype = ContentType.objects.get_for_model(Calendar)
        dcom = DeletionCommand.objects.filter(content_type=ctype).first()

        if dcom is not None:
            if dcom.job.status == Job.STATUS_OK:
                dcom.job.delete()
            else:
                # TODO: if STATUS_ERROR, show a popup with the errors ?
                raise ConflictError(
                    gettext(
                        'A deletion process for an instance of «{model}» already exists.'
                    ).format(model=ctype)
                )

    def form_valid(self, form):
        self.object = form.save()

        return render(
            request=self.request,
            template_name=self.job_template_name,
            context={'job': self.object.job},
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = None
        kwargs['instance_to_delete'] = self.object

        return kwargs


class CalendarLinking(generic.CremeModelEditionPopup):
    model = Activity
    form_class = calendar_forms.ActivityCalendarLinkerForm
    permissions = 'activities'
    pk_url_kwarg = 'activity_id'
    title = _('Change calendar of «{object}»')
