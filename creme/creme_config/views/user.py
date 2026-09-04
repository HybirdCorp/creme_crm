################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2026  Hybird
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

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import DatabaseError
from django.db.transaction import atomic
from django.forms.utils import ErrorList
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.utils.timezone import now
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.views.decorators.debug import sensitive_post_parameters

from creme.creme_core.core.entity_filter import condition_handler
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.models import Workflow, lock
from creme.creme_core.views import generic
from creme.creme_core.views.bricks import BrickStateExtraDataSetting
from creme.creme_core.workflows import (
    FixedUserSource,
    NotificationSendingAction,
)

from .. import bricks, constants
from ..auth import user_config_perm
from ..forms import user as user_forms
from .base import ConfigPortal

logger = logging.getLogger(__name__)


class Portal(ConfigPortal):
    template_name = 'creme_config/portals/user.html'
    permissions = user_config_perm.as_perm
    brick_classes = [bricks.UsersBrick, bricks.TeamsBrick]


class PasswordChange(generic.CremeModelEditionPopup):
    model = get_user_model()
    form_class = user_forms.UserPasswordChangeForm
    pk_url_kwarg = 'user_id'
    permissions = user_config_perm.as_perm
    title = _('Change password for «{object}»')
    title_for_own = _('Change your password')

    @method_decorator(sensitive_post_parameters())
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_title(self) -> str:
        title = self.title_for_own if self.get_object() == self.request.user else self.title

        return title.format(**self.get_title_format_data())


class BaseUserCreation(generic.CremeModelCreationPopup):
    model = get_user_model()
    permissions = user_config_perm.as_perm


class UserCreation(BaseUserCreation):
    form_class = user_forms.UserCreationForm


class TeamCreation(BaseUserCreation):
    form_class = user_forms.TeamCreationForm
    title = _('New team')
    submit_label = _('Save the team')


class BaseUserEdition(generic.CremeModelEditionPopup):
    model = get_user_model()
    pk_url_kwarg = 'user_id'
    permissions = user_config_perm.as_perm

    def get_queryset(self):
        qs = super().get_queryset()

        return qs if self.request.user.is_staff else qs.filter(is_staff=False)


class UserEdition(BaseUserEdition):
    queryset = get_user_model().objects.filter(is_team=False)
    form_class = user_forms.UserEditionForm


class TeamEdition(BaseUserEdition):
    queryset = get_user_model().objects.filter(is_team=True, is_staff=False)
    form_class = user_forms.TeamEditionForm


class UserDeletion(BaseUserEdition):
    """View to delete a User (who can be a Team).

    Objects linked to this User are linked to another User
    (see forms.user.UserAssignationForm).
    """
    form_class = user_forms.UserAssignationForm
    template_name = 'creme_core/generics/blockform/delete-popup.html'
    title = _('Delete «{object}» and assign his entities to user')
    submit_label = _('Delete the user')

    lock_name = 'creme_config-user_transfer'

    def _check_soft_references__workflows(self, instance, user):
        key = instance.portable_key()

        # Conditions ---
        User = get_user_model()
        regular_type_id = condition_handler.RegularFieldConditionHandler.type_id

        def is_referencing_by_condition(workflow):
            for source_conditions in workflow.conditions._conditions_per_source:
                for cond in source_conditions['conditions']:
                    if cond.type == regular_type_id:
                        last_field = cond.handler.field_info[-1]
                        if (
                            last_field.is_relation
                            and issubclass(last_field.related_model, User)
                            and key in cond.value['values']
                        ):
                            return True

            return False

        if conditioned_workflows := {
            wf
            # NB: pre-filter (optimisation)
            for wf in Workflow.objects.filter(json_conditions__regex=f'"{key}"')
            if is_referencing_by_condition(wf)
        }:
            raise PermissionDenied(
                _('This user is used by some conditions of Workflow: {}').format(
                    ', '.join(sorted(wf.title for wf in conditioned_workflows))
                )
            )

        # Actions ---
        def is_referencing_by_action(workflow):
            for action in workflow.actions:
                # TODO: improve Action API to iterate sources => manage other types of action
                if isinstance(action, NotificationSendingAction):
                    source = action.user_source

                    if isinstance(source, FixedUserSource) and source.user == instance:
                        return True

            return False

        if actioned_workflows := {
            wf
            # NB: pre-filter (optimisation)
            for wf in Workflow.objects.filter(json_actions__regex=f'"{key}"')
            if is_referencing_by_action(wf)
        }:
            raise PermissionDenied(
                _('This user is used by some actions of Workflow: {}').format(
                    ', '.join(sorted(wf.title for wf in actioned_workflows))
                )
            )

    def check_instance_permissions(self, instance, user):
        super().check_instance_permissions(instance=instance, user=user)
        # TODO: replace in soft references instead of blocking
        self._check_soft_references__workflows(instance=instance, user=user)

    def get_object(self, *args, **kwargs):
        if int(self.kwargs[self.pk_url_kwarg]) == self.request.user.id:
            raise ConflictError(gettext("You can't delete the current user."))

        return super().get_object(*args, **kwargs)

    def post(self, *args, **kwargs):
        try:
            # We create the lock out-of the super-post() transaction
            with lock.MutexAutoLock(self.lock_name):
                return super().post(*args, **kwargs)
        except (DatabaseError, lock.MutexLockedException) as e:
            logger.exception('UserDeletion: an error occurred')

            return HttpResponse(
                _('You cannot delete this user. [original error: {}]').format(e),
                status=400,
            )


class UserDeactivation(generic.CheckedView):
    user_id_url_kwarg = 'user_id'
    permissions = user_config_perm.as_perm

    def post(self, request, **kwargs):
        user_id = self.kwargs[self.user_id_url_kwarg]
        user = request.user

        if int(user_id) == user.id:
            raise ConflictError(gettext("You can't deactivate the current user."))

        with atomic():
            user_to_deactivate = get_object_or_404(
                get_user_model().objects.select_for_update(), id=user_id,
            )

            if user_to_deactivate.is_staff and not user.is_staff:
                return HttpResponse(
                    gettext("You can't deactivate a staff user."),
                    status=409,
                )

            if user_to_deactivate.is_active:
                user_to_deactivate.is_active = False
                user_to_deactivate.deactivated_on = now()
                user_to_deactivate.save()

        return HttpResponse()


class UserActivation(generic.CheckedView):
    user_id_url_kwarg = 'user_id'
    permissions = user_config_perm.as_perm

    def post(self, request, **kwargs):
        user_id = self.kwargs[self.user_id_url_kwarg]
        model = get_user_model()

        with atomic():
            user_to_activate = get_object_or_404(
                model.objects.select_for_update(), id=user_id,
            )

            if user_to_activate.is_staff and not request.user.is_staff:
                return HttpResponse(
                    gettext("You can't activate a staff user."),
                    status=409,
                )

            if not user_to_activate.is_active:
                user_to_activate.is_active = True
                user_to_activate.deactivated_on = None

                try:
                    user_to_activate.clean()
                except ValidationError as e:
                    return HttpResponse(ErrorList(e.messages).as_ul(), status=409)

                user_to_activate.save()

        return HttpResponse()


class HideInactiveUsers(BrickStateExtraDataSetting):
    brick_cls = bricks.UsersBrick
    data_key = constants.BRICK_STATE_HIDE_INACTIVE_USERS
