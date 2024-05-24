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
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme.creme_core.auth import build_creation_perm
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.models import Relation, RelationType, SettingValue
from creme.creme_core.models.utils import assign_2_charfield
from creme.creme_core.views import generic
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
        if entity == user.linked_contact:
            raise ConflictError(gettext(
                'The current contact is you; '
                'the button has to be used with a different contact'
            ))

    @atomic
    def post(self, request, *args, **kwargs):
        user = request.user
        contact = self.get_related_entity()

        try:
            values = SettingValue.objects.get_4_keys(
                {'key': setting_keys.unsuccessful_subtype_key},
                {'key': setting_keys.unsuccessful_status_key},
                {'key': setting_keys.unsuccessful_title_key},
                {'key': setting_keys.unsuccessful_duration_key},
            )

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
        activity.save()

        create_rel = partial(
            Relation.objects.create,
            user=user,
            type=RelationType.objects.get(id=constants.REL_SUB_PART_2_ACTIVITY),
            object_entity=activity,
        )
        create_rel(subject_entity=user.linked_contact)
        create_rel(subject_entity=contact)

        activity.calendars.add(Calendar.objects.get_default_calendar(user))

        return HttpResponse()


class UnsuccessfulPhoneCallConfiguration(generic.CremeFormPopup):
    form_class = buttons_forms.UnsuccessfulPhoneCallConfigForm
    permissions = 'activities.can_admin'
    title = _('Edit the configuration of the button')
    submit_label = _('Save the modifications')
