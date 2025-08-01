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

from __future__ import annotations

from datetime import timedelta
from functools import partial

from django.core.exceptions import ObjectDoesNotExist
from django.db.transaction import atomic
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.utils.timezone import now
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme.creme_core.auth import build_creation_perm
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.models import CremeEntity, Relation, SettingValue
from creme.creme_core.models.utils import assign_2_charfield
from creme.creme_core.views import generic
from creme.creme_core.views.decorators import workflow_engine
from creme.persons import get_contact_model

from .. import constants, get_activity_model, setting_keys
from ..forms import buttons as buttons_forms
from ..models import ActivitySubType, Calendar, Status

Activity = get_activity_model()


class UnsuccessfulPhoneCallCreation(generic.base.EntityRelatedMixin, generic.CheckedView):
    permissions = ['activities', build_creation_perm(Activity)]
    entity_id_url_kwarg = 'contact_id'
    entity_classes = get_contact_model()

    def check_related_entity_permissions(self, entity, user):
        user.has_perm_to_link_or_die(entity)

    def _get_participants(self, user, entity: CremeEntity) -> list[CremeEntity]:
        linked_contact = user.linked_contact

        if entity == linked_contact:
            raise ConflictError(gettext(
                'The current contact is you; '
                'the button has to be used with a different contact'
            ))

        return [linked_contact, entity]

    def _get_subjects(self, user, entity: CremeEntity) -> list[CremeEntity]:
        return []

    def _get_linked_entities(self, user, entity: CremeEntity) -> list[CremeEntity]:
        return []

    def _get_setting_values(self):
        return SettingValue.objects.get_4_keys(
            {'key': setting_keys.unsuccessful_subtype_key},
            {'key': setting_keys.unsuccessful_status_key},
            {'key': setting_keys.unsuccessful_title_key},
            {'key': setting_keys.unsuccessful_duration_key},
        )

    def _build_activity(self, user) -> Activity:
        try:
            self.setting_values = values = self._get_setting_values()

            sub_type = ActivitySubType.objects.get(
                uuid=values[setting_keys.unsuccessful_subtype_key.id].value,
            )
            status = Status.objects.get(
                uuid=values[setting_keys.unsuccessful_status_key.id].value,
            )
        except ObjectDoesNotExist:
            raise ConflictError(gettext(
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
                minutes=values[setting_keys.unsuccessful_duration_key.id].value,
            ),
            end=now_value,
        )
        assign_2_charfield(
            activity,
            field_name='title',
            value=values[setting_keys.unsuccessful_title_key.id].value,
        )

        return activity

    def _pre_creation(self, user, entity):
        self.participants = self._get_participants(user=user, entity=entity)
        self.subjects = self._get_subjects(user=user, entity=entity)
        self.linked_entities = self._get_linked_entities(user=user, entity=entity)

    def _post_creation_relations(self, user, activity):
        build_rel = partial(Relation, user=user, object_entity=activity)
        Relation.objects.safe_multi_save(
            [
                *(
                    build_rel(
                        subject_entity=subject, type_id=constants.REL_SUB_ACTIVITY_SUBJECT
                    ) for subject in self.subjects
                ),
                *(
                    build_rel(
                        subject_entity=participant, type_id=constants.REL_SUB_PART_2_ACTIVITY
                    ) for participant in self.participants
                ),
                *(
                    build_rel(
                        subject_entity=linked_entity,
                        type_id=constants.REL_SUB_LINKED_2_ACTIVITY,
                    ) for linked_entity in self.linked_entities
                ),
            ],
            check_existing=False,
        )

    def _post_creation_calendar(self, user, activity):
        activity.calendars.add(Calendar.objects.get_default_calendar(user))

    def _post_creation(self, user, activity):
        self._post_creation_relations(user=user, activity=activity)
        self._post_creation_calendar(user=user, activity=activity)

    @atomic
    @method_decorator(workflow_engine)
    def post(self, request, *args, **kwargs):
        entity = self.get_related_entity()
        user = request.user
        self._pre_creation(user=user, entity=entity)

        activity = self._build_activity(user)
        activity.save()
        self._post_creation(user=user, activity=activity)

        return HttpResponse()


class UnsuccessfulPhoneCallConfiguration(generic.CremeFormPopup):
    form_class = buttons_forms.UnsuccessfulPhoneCallConfigForm
    permissions = 'activities.can_admin'
    title = _('Edit the configuration of the button')
    submit_label = _('Save the modifications')
