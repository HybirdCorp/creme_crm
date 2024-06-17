################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2024  Hybird
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

from __future__ import annotations

from datetime import timedelta
from functools import partial

from django.core.exceptions import ObjectDoesNotExist
from django.db.transaction import atomic
from django.http import HttpResponse
from django.utils.timezone import now
from django.utils.translation import gettext as _

from creme.activities import get_activity_model
from creme.activities import setting_keys as act_keys
from creme.activities.constants import (
    REL_SUB_ACTIVITY_SUBJECT,
    REL_SUB_PART_2_ACTIVITY,
)
from creme.activities.models import ActivitySubType, Calendar, Status
from creme.creme_core.auth import build_creation_perm
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.models import Relation, SettingValue
from creme.creme_core.models.utils import assign_2_charfield
from creme.creme_core.views import generic
from creme.opportunities import get_opportunity_model
from creme.opportunities.constants import REL_OBJ_LINKED_CONTACT

Activity = get_activity_model()


# TODO: factorise?
class UnsuccessfulPhoneCallCreation(generic.base.EntityRelatedMixin, generic.CheckedView):
    permissions = ['opportunities', build_creation_perm(Activity)]
    entity_id_url_kwarg = 'opp_id'
    entity_classes = get_opportunity_model()

    def check_related_entity_permissions(self, entity, user):
        user.has_perm_to_link_or_die(entity)

    # TODO: split in several methods
    # TODO: shrink atomic context around creation (i.e. check errors outside)
    @atomic
    def post(self, request, *args, **kwargs):
        user = request.user
        user_contact = user.linked_contact
        opp = self.get_related_entity()

        try:
            participant_ids = set(map(int, request.POST.getlist('participant')))
        except ValueError as e:
            raise ConflictError(f'Invalid participant ID: {e}')

        if participant_ids:
            # TODO: error if only one participant is invalid?
            def accept_participant(contact):
                return contact.id in participant_ids
        else:
            def accept_participant(contact):
                return True

        participants = [
            contact
            for rel in opp.get_relations(REL_OBJ_LINKED_CONTACT, real_obj_entities=True)
            if (contact := rel.real_object) != user_contact
            and not contact.is_deleted
            and accept_participant(contact)
        ]
        if not participants:
            raise ConflictError(_(
                'The phone call cannot be created because no other participant '
                'than you has been found (notice that deleted contact are ignored).'
            ))

        try:
            values = SettingValue.objects.get_4_keys(
                {'key': act_keys.unsuccessful_subtype_key},
                {'key': act_keys.unsuccessful_status_key},
                {'key': act_keys.unsuccessful_title_key},
                {'key': act_keys.unsuccessful_duration_key},
            )

            sub_type = ActivitySubType.objects.get(
                uuid=values[act_keys.unsuccessful_subtype_key.id].value,
            )
            status = Status.objects.get(
                uuid=values[act_keys.unsuccessful_status_key.id].value,
            )
        except ObjectDoesNotExist:
            raise ConflictError(_(
                'The configuration of the button is broken; '
                'fix it in the configuration of «Activities».'
            ))

        now_value = now()

        # NB: notice that we do not check FieldsConfig for required fields;
        #     so we bypass the optional extra rules at creation (at edition the
        #     rules will have to be respected by the way).
        activity = Activity(
            user=user, status=status,
            type=sub_type.type, sub_type=sub_type,
            start=now_value - timedelta(
                minutes=values[act_keys.unsuccessful_duration_key.id].value,
            ),
            end=now_value,
        )
        assign_2_charfield(
            activity,
            field_name='title',
            value=values[act_keys.unsuccessful_title_key.id].value,
        )
        activity.save()

        build_rel = partial(Relation, user=user, object_entity=activity)
        Relation.objects.safe_multi_save(
            [
                build_rel(subject_entity=opp, type_id=REL_SUB_ACTIVITY_SUBJECT),
                build_rel(subject_entity=user_contact, type_id=REL_SUB_PART_2_ACTIVITY),
                *(
                    build_rel(subject_entity=contact, type_id=REL_SUB_PART_2_ACTIVITY)
                    for contact in participants
                )
            ],
            check_existing=False,
        )

        activity.calendars.add(Calendar.objects.get_default_calendar(user))

        return HttpResponse()
