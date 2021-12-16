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

from datetime import time
from functools import partial
from typing import Type, Union

from dateutil.parser import isoparse
from django.db.models import Q
from django.forms.forms import BaseForm
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.utils.timezone import get_current_timezone, is_naive, make_naive
from django.utils.translation import gettext_lazy as _

from creme.creme_core.auth import EntityCredentials
from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.auth.decorators import (
    login_required,
    permission_required,
)
from creme.creme_core.gui.custom_form import CustomFormDescriptor
from creme.creme_core.gui.listview import CreationButton
from creme.creme_core.http import CremeJsonResponse
from creme.creme_core.models import CremeEntity, RelationType
from creme.creme_core.utils import bool_from_str_extended, get_from_GET_or_404
from creme.creme_core.views import generic
from creme.creme_core.views.generic import base
from creme.persons import get_contact_model

from .. import constants, custom_forms, get_activity_model
from ..forms import activity as act_forms
from ..models import ActivitySubType, ActivityType
from ..utils import get_ical

Activity = get_activity_model()

_CREATION_PERM_STR = cperm(Activity)
# _TYPES_MAP = {
#     'meeting':   constants.ACTIVITYTYPE_MEETING,
#     'phonecall': constants.ACTIVITYTYPE_PHONECALL,
#     'task':      constants.ACTIVITYTYPE_TASK,
# }


class ActivityCreation(generic.EntityCreation):
    model = Activity
    form_class: Union[Type[BaseForm], CustomFormDescriptor] = custom_forms.ACTIVITY_CREATION_CFORM
    type_name_url_kwarg = 'act_type'

    allowed_activity_types = {
        'meeting':   constants.ACTIVITYTYPE_MEETING,
        'phonecall': constants.ACTIVITYTYPE_PHONECALL,
        'task':      constants.ACTIVITYTYPE_TASK,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.type_id = None

    def get(self, request, *args, **kwargs):
        self.type_id = self.get_type_id()
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.type_id = self.get_type_id()
        return super().post(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['activity_type_id'] = self.type_id

        return kwargs

    def get_type_id(self):
        act_type = self.kwargs.get(self.type_name_url_kwarg)

        if act_type is None:
            type_id = None
        else:
            # type_id = _TYPES_MAP.get(act_type)
            type_id = self.allowed_activity_types.get(act_type)

            if not type_id:
                raise Http404(f'No activity type matches with: {act_type}')

        return type_id

    def get_title(self):
        return Activity.get_creation_title(self.type_id)


class ActivityCreationPopup(generic.EntityCreationPopup):
    model = Activity
    form_class = custom_forms.ACTIVITY_CREATION_FROM_CALENDAR_CFORM

    def get_initial(self):
        initial = super().get_initial()
        request = self.request

        if request.method == 'GET':
            tz = get_current_timezone()
            get = partial(get_from_GET_or_404, GET=request.GET)
            initial['is_all_day'] = get(
                key='allDay', default='0', cast=bool_from_str_extended,
            )

            def isoparse_naive(value):
                if value is not None:
                    value = isoparse(value)

                    if not is_naive(value):
                        value = make_naive(value, tz)

                return value

            def _set_datefield(request_key, field_name, **kwargs):
                value = get(key=request_key, cast=isoparse_naive, **kwargs)

                if value:
                    initial[field_name] = (
                        value.date(),
                        time(hour=value.hour, minute=value.minute)
                        if value.hour or value.minute else
                        None,
                    )

            model = self.model
            _set_datefield(
                request_key='start',
                field_name=act_forms.StartSubCell(model=model).into_cell().key,
            )
            _set_datefield(
                request_key='end',
                field_name=act_forms.EndSubCell(model=model).into_cell().key,
                default=None,
            )

        return initial


class UnavailabilityCreation(ActivityCreation):
    form_class = custom_forms.UNAVAILABILITY_CREATION_FROM

    def get_type_id(self):
        return constants.ACTIVITYTYPE_INDISPO


class RelatedActivityCreation(ActivityCreation):
    form_class = custom_forms.ACTIVITY_CREATION_CFORM
    entity_pk_url_kwargs = 'entity_id'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.related_entity = None
        self.rtype_id = None

    def get(self, request, *args, **kwargs):
        self.related_entity = self.get_related_entity()
        self.rtype_id = self.get_rtype_id()
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.related_entity = self.get_related_entity()
        self.rtype_id = self.get_rtype_id()
        return super().post(request, *args, **kwargs)

    def get_initial(self):
        initial = super(RelatedActivityCreation, self).get_initial()

        related_entity = self.related_entity
        rtype_id = self.rtype_id

        def get_key(subcell_cls):
            return subcell_cls(model=self.model).into_cell().key

        if rtype_id == constants.REL_SUB_PART_2_ACTIVITY:
            if related_entity.is_user:
                initial[get_key(act_forms.ParticipatingUsersSubCell)] = [related_entity.is_user]
            else:
                initial[get_key(act_forms.OtherParticipantsSubCell)] = [related_entity]
        elif rtype_id == constants.REL_SUB_ACTIVITY_SUBJECT:
            initial[get_key(act_forms.ActivitySubjectsSubCell)] = [related_entity]
        else:
            initial[get_key(act_forms.LinkedEntitiesSubCell)] = [related_entity]

        return initial

    def get_related_entity(self):
        entity = get_object_or_404(
            CremeEntity,
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
            rtype_id = (
                constants.REL_SUB_ACTIVITY_SUBJECT
                if rtype.is_compatible(entity) else
                constants.REL_SUB_LINKED_2_ACTIVITY
            )  # Not custom, & all ContentTypes should be accepted

        return rtype_id

    # def get_success_url(self):
    #     return self.related_entity.get_absolute_url()

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
    form_class = custom_forms.ACTIVITY_EDITION_CFORM
    pk_url_kwarg = 'activity_id'


class ActivitiesList(generic.EntitiesList):
    model = Activity
    default_headerfilter_id = constants.DEFAULT_HFILTER_ACTIVITY


class TypedActivitiesList(ActivitiesList):
    creation_label = 'Create a typed activity'
    creation_url = '/activities/typed_activity/create/'

    def get_buttons(self):
        class TypedActivityCreationButton(CreationButton):
            def get_label(this, request, model):
                return self.creation_label

            def get_url(this, request, model):
                return self.creation_url

        return super().get_buttons().replace(
            old=CreationButton, new=TypedActivityCreationButton,
        )


class PhoneCallsList(TypedActivitiesList):
    title = _('List of phone calls')
    creation_label = _('Create a phone call')
    creation_url = reverse_lazy('activities__create_activity', args=('phonecall',))
    internal_q = Q(type=constants.ACTIVITYTYPE_PHONECALL)


class MeetingsList(TypedActivitiesList):
    title = _('List of meetings')
    creation_label = _('Create a meeting')
    creation_url = reverse_lazy('activities__create_activity', args=('meeting',))
    internal_q = Q(type=constants.ACTIVITYTYPE_MEETING)


@login_required
@permission_required('activities')
def download_ical(request):
    act_ids = request.GET.getlist('id')

    # TODO: is_deleted=False ??
    activities = EntityCredentials.filter(
        queryset=Activity.objects.filter(pk__in=act_ids), user=request.user,
    )
    # response = HttpResponse(get_ical(activities), content_type='text/calendar')
    # response['Content-Disposition'] = 'attachment; filename=Calendar.ics'
    #
    # return response
    return HttpResponse(
        get_ical(activities),
        headers={
            'Content-Type': 'text/calendar',
            'Content-Disposition': 'attachment; filename="Calendar.ics"',
        },
    )


class TypeChoices(base.CheckedView):
    response_class = CremeJsonResponse
    # permissions = 'activities' TODO ?
    type_id_url_kwarg = 'type_id'

    def get_choices(self):
        type_id = self.kwargs[self.type_id_url_kwarg]

        if not type_id:
            return []

        get_object_or_404(ActivityType, pk=type_id)

        return [
            *ActivitySubType.objects.filter(type=type_id).values_list('id', 'name'),
        ]

    def get(self, request, *args, **kwargs):
        return self.response_class(
            self.get_choices(),
            safe=False,  # Result is not a dictionary
        )
