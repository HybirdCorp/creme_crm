# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2020  Hybird
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
from functools import partial
from typing import Type

from dateutil.parser import isoparse

from django.db.models import Q
from django.forms.forms import BaseForm
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.utils.timezone import get_current_timezone, make_naive, is_naive
from django.utils.translation import gettext_lazy as _

from creme.creme_core.auth import EntityCredentials
from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.gui.listview import CreationButton
from creme.creme_core.http import CremeJsonResponse
from creme.creme_core.models import CremeEntity, RelationType
from creme.creme_core.utils import get_from_GET_or_404, bool_from_str_extended
from creme.creme_core.views import generic
from creme.creme_core.views.generic import base

from creme.persons import get_contact_model

from .. import get_activity_model, constants
from ..forms import activity as act_forms
from ..models import ActivityType, ActivitySubType
from ..utils import get_ical

Activity = get_activity_model()

_CREATION_PERM_STR = cperm(Activity)
_TYPES_MAP = {
    'meeting':   constants.ACTIVITYTYPE_MEETING,
    'phonecall': constants.ACTIVITYTYPE_PHONECALL,
    'task':      constants.ACTIVITYTYPE_TASK,
}


class ActivityCreation(generic.EntityCreation):
    model = Activity
    form_class: Type[BaseForm] = act_forms.ActivityCreateForm
    template_name = 'activities/add_activity_form.html'
    type_name_url_kwarg = 'act_type'
    form_template_name = 'activities/frags/activity_form_content.html'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.type_id = None

    def get(self, request, *args, **kwargs):
        self.type_id = self.get_type_id()
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.type_id = self.get_type_id()
        return super().post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['content_template'] = self.form_template_name

        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['activity_type_id'] = self.type_id

        return kwargs

    def get_type_id(self):
        act_type = self.kwargs.get(self.type_name_url_kwarg)

        if act_type is None:
            type_id = None
        else:
            type_id = _TYPES_MAP.get(act_type)  # TODO: self.TYPES_MAP ?

            if not type_id:
                raise Http404(f'No activity type matches with: {act_type}')

        return type_id

    def get_title(self):
        return Activity.get_creation_title(self.type_id)


class ActivityCreationPopup(generic.EntityCreationPopup):
    model = Activity
    form_class = act_forms.CalendarActivityCreateForm
    template_name = 'activities/forms/add-activity-popup.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        request = self.request
        tz = get_current_timezone()

        def isoparse_naive(value):
            if value is not None:
                value = isoparse(value)

                if not is_naive(value):
                    value = make_naive(value, tz)

            return value

        if request.method == 'GET':
            get = partial(get_from_GET_or_404, GET=request.GET)
            allDay = get(key='allDay', default='0', cast=bool_from_str_extended)
            start = get(key='start', cast=isoparse_naive)
            end = get(key='end', default=None, cast=isoparse_naive)

            kwargs.update(
                start=start,
                end=end,
                is_all_day=allDay
            )

        return kwargs


class UnavailabilityCreation(ActivityCreation):
    form_class = act_forms.IndisponibilityCreateForm
    form_template_name = 'activities/frags/indispo_form_content.html'

    def get_type_id(self):
        return constants.ACTIVITYTYPE_INDISPO


class RelatedActivityCreation(ActivityCreation):
    form_class = act_forms.RelatedActivityCreateForm
    entity_pk_url_kwargs = 'entity_id'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.related_entity = None
        self.rtype_id       = None

    def get(self, request, *args, **kwargs):
        self.related_entity = self.get_related_entity()
        self.rtype_id       = self.get_rtype_id()
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.related_entity = self.get_related_entity()
        self.rtype_id = self.get_rtype_id()
        return super().post(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['related_entity']   = self.related_entity
        kwargs['relation_type_id'] = self.rtype_id

        return kwargs

    def get_related_entity(self):
        entity = get_object_or_404(CremeEntity,
                                   pk=self.kwargs[self.entity_pk_url_kwargs],
                                  ).get_real_entity()
        self.request.user.has_perm_to_link_or_die(entity)

        return entity

    def get_rtype_id(self):
        entity = self.related_entity

        if isinstance(entity, get_contact_model()):
            rtype_id = constants.REL_SUB_PART_2_ACTIVITY
        else:
            rtype = RelationType.objects.get(pk=constants.REL_SUB_ACTIVITY_SUBJECT)
            rtype_id = constants.REL_SUB_ACTIVITY_SUBJECT \
                       if rtype.is_compatible(entity) else \
                       constants.REL_SUB_LINKED_2_ACTIVITY  # Not custom, & all ContentTypes should be accepted

        return rtype_id

    def get_success_url(self):
        # TODO: use 'cancel_url' if it is set ?
        return self.related_entity.get_absolute_url()

    def get_type_id(self):
        type_id = self.request.GET.get('activity_type')  # TODO: attribute

        if type_id:
            get_object_or_404(ActivityType, pk=type_id)

        return type_id


class ActivityDetail(generic.EntityDetail):
    model = Activity
    template_name = 'activities/view_activity.html'
    pk_url_kwarg = 'activity_id'


class ActivityPopup(generic.EntityDetailPopup):
    model = Activity
    template_name = 'activities/activity-popup.html'
    pk_url_kwarg = 'activity_id'


class ActivityEdition(generic.EntityEdition):
    model = Activity
    form_class = act_forms.ActivityEditForm
    pk_url_kwarg = 'activity_id'


class ActivitiesList(generic.EntitiesList):
    model = Activity
    default_headerfilter_id = constants.DEFAULT_HFILTER_ACTIVITY


class TypedActivitiesList(ActivitiesList):
    creation_label = 'Create a typed activity'
    creation_url   = '/activities/typed_activity/create/'

    def get_buttons(self):
        class TypedActivityCreationButton(CreationButton):
            def get_label(this, request, model):
                return self.creation_label

            def get_url(this, request, model):
                return self.creation_url

        return super().get_buttons()\
                      .replace(old=CreationButton, new=TypedActivityCreationButton)


class PhoneCallsList(TypedActivitiesList):
    title = _('List of phone calls')
    creation_label = _('Create a phone call')
    creation_url   = reverse_lazy('activities__create_activity', args=('phonecall',))
    internal_q = Q(type=constants.ACTIVITYTYPE_PHONECALL)


class MeetingsList(TypedActivitiesList):
    title = _('List of meetings')
    creation_label = _('Create a meeting')
    creation_url   = reverse_lazy('activities__create_activity', args=('meeting',))
    internal_q = Q(type=constants.ACTIVITYTYPE_MEETING)


@login_required
@permission_required('activities')
def download_ical(request):
    act_ids = request.GET.getlist('id')

    # TODO: is_deleted=False ??
    activities = EntityCredentials.filter(queryset=Activity.objects.filter(pk__in=act_ids),
                                          user=request.user,
                                         )
    response = HttpResponse(get_ical(activities), content_type='text/calendar')
    response['Content-Disposition'] = 'attachment; filename=Calendar.ics'

    return response


class TypeChoices(base.CheckedView):
    response_class = CremeJsonResponse
    # permissions = 'activities' TODO ?
    type_id_url_kwarg = 'type_id'

    def get_choices(self):
        type_id = self.kwargs[self.type_id_url_kwarg]

        if not type_id:
            return []

        get_object_or_404(ActivityType, pk=type_id)

        return [*ActivitySubType.objects
                                .filter(type=type_id)
                                .values_list('id', 'name')
               ]

    def get(self, request, *args, **kwargs):
        return self.response_class(
            self.get_choices(),
            safe=False,  # Result is not a dictionary
        )
