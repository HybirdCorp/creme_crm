################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2024-2025  Hybird
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

from django.utils.translation import gettext as _

from creme.activities import get_activity_model
from creme.activities.views import buttons as activity_views
from creme.creme_core.auth import build_creation_perm
from creme.creme_core.core.exceptions import ConflictError
from creme.opportunities import get_opportunity_model
from creme.opportunities.constants import REL_OBJ_LINKED_CONTACT

Activity = get_activity_model()


class UnsuccessfulPhoneCallCreation(activity_views.UnsuccessfulPhoneCallCreation):
    permissions = ['opportunities', build_creation_perm(Activity)]
    entity_id_url_kwarg = 'opp_id'
    entity_classes = get_opportunity_model()

    def _get_participants(self, user, entity):
        try:
            participant_ids = set(map(int, self.request.POST.getlist('participant')))
        except ValueError as e:
            raise ConflictError(f'Invalid participant ID: {e}')

        if participant_ids:
            # TODO: error if only one participant is invalid?
            def accept_participant(contact):
                return contact.id in participant_ids
        else:
            def accept_participant(contact):
                return True

        user_contact = user.linked_contact
        participants = [
            contact
            for rel in entity.get_relations(REL_OBJ_LINKED_CONTACT, real_obj_entities=True)
            if (contact := rel.real_object) != user_contact
            and not contact.is_deleted
            and accept_participant(contact)
        ]
        if not participants:
            raise ConflictError(_(
                'The phone call cannot be created because no other participant '
                'than you has been found (notice that deleted contact are ignored).'
            ))

        return [user_contact, *participants]

    def _get_subjects(self, user, entity):
        return [entity]
