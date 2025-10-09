################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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

from datetime import timedelta
from functools import partial

from django.db.transaction import atomic
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.html import format_html
from django.utils.timezone import now
from django.utils.translation import gettext as _

import creme.activities.constants as act_constants
from creme import activities, persons
from creme.activities.models import ActivitySubType, Calendar, Status
from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.core.workflow import run_workflow_engine
from creme.creme_core.http import CremeJsonResponse
from creme.creme_core.models import Relation, RelationType
from creme.creme_core.shortcuts import get_bulk_or_404
from creme.creme_core.utils import get_from_GET_or_404, get_from_POST_or_404
from creme.creme_core.views import generic
from creme.creme_core.views.bricks import BricksReloading
from creme.persons.views.contact import ContactCreation
from creme.persons.views.organisation import OrganisationCreation

from .bricks import CallersBrick

Contact = persons.get_contact_model()
Activity = activities.get_activity_model()


class CTIPersonMixin:
    number_url_kwarg = 'number'

    def get_initial(self):
        initial = super().get_initial()
        initial['phone'] = self.kwargs[self.number_url_kwarg]

        return initial


class CTIContactCreation(CTIPersonMixin, ContactCreation):
    pass


class CTIOrganisationCreation(CTIPersonMixin, OrganisationCreation):
    pass


class AnswerToACall(generic.BricksView):
    template_name = 'cti/respond_to_a_call.html'
    bricks = [CallersBrick]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.number = None

    def get_bricks_reload_url(self):
        return reverse('cti__reload_callers_brick', args=(self.get_number(),))

    def get_bricks(self):
        return {'main': [brick_cls() for brick_cls in self.bricks]}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['number'] = self.get_number()

        return context

    def get_number(self) -> str:
        number = self.number

        if number is None:
            self.number = number = get_from_GET_or_404(self.request.GET, 'number')

        return number


class CallersBrickReloading(BricksReloading):
    number_url_kwarg = 'number'
    bricks = AnswerToACall.bricks

    # TODO: factorise (sms, EmailSending)?
    def get_bricks(self):
        # return [CallersBrick()]
        bricks = []
        allowed_bricks = {brick_cls.id: brick_cls for brick_cls in self.bricks}

        for brick_id in self.get_brick_ids():
            try:
                brick_cls = allowed_bricks[brick_id]
            except KeyError as e:
                raise Http404('Invalid brick ID') from e

            bricks.append(brick_cls())

        return bricks

    def get_bricks_context(self):
        context = super().get_bricks_context()
        context['number'] = self.kwargs[self.number_url_kwarg]

        return context


class PhoneCallCreation(generic.base.EntityRelatedMixin,
                        generic.base.TitleMixin,
                        generic.CheckedView):
    permissions = ['activities', cperm(Activity)]
    phonecall_status_uuid = act_constants.UUID_STATUS_IN_PROGRESS
    phonecall_subtype_uuid = act_constants.UUID_SUBTYPE_PHONECALL_INCOMING
    title = _('Call to {entity}')  # Phone Call title

    def check_related_entity_permissions(self, entity, user):
        user.has_perm_to_link_or_die(entity)

    def build_phonecall(self):
        now_value = now()
        sub_type = get_object_or_404(ActivitySubType, uuid=self.get_phonecall_subtype_uuid())

        return Activity(
            user=self.request.user,
            title=self.get_title(),
            description=_('Automatically created by CTI'),
            status=get_object_or_404(Status, uuid=self.get_phonecall_status_uuid()),
            type_id=sub_type.type_id,
            sub_type=sub_type,
            start=now_value,
            # TODO: attribute ? ActivityType.default_hour_duration ?
            end=now_value + timedelta(minutes=5),
        )

    def create_related_phonecall(self):
        user = self.request.user
        user_contact = user.linked_contact
        if user_contact is None:
            raise Http404(_('Staff users cannot create phone call'))

        users = [user]
        entity = self.get_related_entity()

        pcall = self.build_phonecall()

        with atomic(), run_workflow_engine(user=user):
            pcall.save()

            # If the entity is a contact with related user, should add the
            # phone call to his calendar
            if isinstance(entity, Contact) and entity.is_user:
                users.append(entity.is_user)

            pcall.calendars.add(*Calendar.objects.get_default_calendars(users).values())

            # TODO: link credentials
            caller_rtype = act_constants.REL_SUB_PART_2_ACTIVITY
            entity_rtype = (
                act_constants.REL_SUB_PART_2_ACTIVITY
                if isinstance(entity, Contact) else
                act_constants.REL_SUB_LINKED_2_ACTIVITY
            )
            rtypes_map = get_bulk_or_404(RelationType, id_list=[caller_rtype, entity_rtype])

            create_rel = partial(Relation.objects.create, object_entity=pcall, user=user)

            if entity.pk != user_contact.pk:
                create_rel(subject_entity=user_contact, type=rtypes_map[caller_rtype])
            create_rel(subject_entity=entity, type=rtypes_map[entity_rtype])

        return pcall

    def get_phonecall_status_uuid(self) -> str:
        return self.phonecall_status_uuid

    def get_phonecall_subtype_uuid(self) -> str:
        return self.phonecall_subtype_uuid

    def get_title_format_data(self):
        return {'entity': self.get_related_entity()}

    def post(self, *args, **kwargs):
        return redirect(self.create_related_phonecall())


class AsCallerPhoneCallCreation(PhoneCallCreation):
    response_class = CremeJsonResponse
    entity_id_arg = 'entity_id'
    phonecall_subtype_uuid = act_constants.UUID_SUBTYPE_PHONECALL_OUTGOING

    def get_related_entity_id(self):
        return get_from_POST_or_404(self.request.POST, self.entity_id_arg)

    def post(self, request, *args, **kwargs):
        pcall = self.create_related_phonecall()

        return self.response_class(  # TODO: useful ??
            format_html(
                '{msg}<br/><a href="{url}">{pcall}</a>',
                msg=_('Phone call successfully created.'),
                url=pcall.get_absolute_url(),
                pcall=pcall,
            ),
            safe=False,  # Result is not a dictionary
        )
