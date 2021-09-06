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

from django.contrib.auth import get_user_model
# from django.db import IntegrityError
from django.db import DatabaseError
from django.db.transaction import atomic
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

# from creme.creme_core import utils
from creme.creme_core.auth import SUPERUSER_PERM
from creme.creme_core.core.exceptions import ConflictError
# from creme.creme_core.models import BrickState
from creme.creme_core.models import lock
from creme.creme_core.views import generic
from creme.creme_core.views.bricks import BrickStateExtraDataSetting

from ..bricks import UsersBrick
from ..constants import BRICK_STATE_HIDE_INACTIVE_USERS
from ..forms import user as user_forms

logger = logging.getLogger(__name__)


class PasswordChange(generic.CremeModelEditionPopup):
    model = get_user_model()
    form_class = user_forms.UserChangePwForm
    pk_url_kwarg = 'user_id'
    permissions = SUPERUSER_PERM
    title = _('Change password for «{object}»')


class BaseUserCreation(generic.CremeModelCreationPopup):
    model = get_user_model()
    permissions = SUPERUSER_PERM


class UserCreation(BaseUserCreation):
    form_class = user_forms.UserAddForm


class TeamCreation(BaseUserCreation):
    form_class = user_forms.TeamCreateForm
    title = _('New team')
    submit_label = _('Save the team')


class Portal(generic.BricksView):
    template_name = 'creme_config/portals/user.html'


class BaseUserEdition(generic.CremeModelEditionPopup):
    model = get_user_model()
    pk_url_kwarg = 'user_id'
    permissions = SUPERUSER_PERM

    def get_queryset(self):
        qs = super().get_queryset()

        return qs if self.request.user.is_staff else qs.filter(is_staff=False)


class UserEdition(BaseUserEdition):
    queryset = get_user_model().objects.filter(is_team=False)
    form_class = user_forms.UserEditForm


class TeamEdition(BaseUserEdition):
    queryset = get_user_model().objects.filter(is_team=True, is_staff=False)
    form_class = user_forms.TeamEditForm


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

    def get_object(self, *args, **kwargs):
        if int(self.kwargs[self.pk_url_kwarg]) == self.request.user.id:
            raise ConflictError(gettext("You can't delete the current user."))

        return super(UserDeletion, self).get_object(*args, **kwargs)

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
    permissions = SUPERUSER_PERM

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
                    gettext("You can't deactivate a staff user."), status=400,
                )

            if user_to_deactivate.is_active:
                user_to_deactivate.is_active = False
                user_to_deactivate.save()

        return HttpResponse()


class UserActivation(generic.CheckedView):
    user_id_url_kwarg = 'user_id'
    permissions = SUPERUSER_PERM

    def post(self, request, **kwargs):
        user_id = self.kwargs[self.user_id_url_kwarg]

        with atomic():
            user_to_activate = get_object_or_404(
                get_user_model().objects.select_for_update(), id=user_id,
            )

            if user_to_activate.is_staff and not request.user.is_staff:
                return HttpResponse(
                    gettext("You can't activate a staff user."), status=400,
                )

            if not user_to_activate.is_active:
                user_to_activate.is_active = True
                user_to_activate.save()

        return HttpResponse()


# class HideInactiveUsers(generic.CheckedView):
#     value_arg = 'value'
#     brick_cls = UsersBrick
#
#     def post(self, request, **kwargs):
#         value = utils.get_from_POST_or_404(
#             request.POST,
#             key=self.value_arg,
#             cast=utils.bool_from_str_extended,
#         )
#
#         # NB: we can still have a race condition because we do not use
#         #     select_for_update ; but it's a state related to one user & one brick,
#         #     so it would not be a real world problem.
#         for _i in range(10):
#             state = BrickState.objects.get_for_brick_id(
#                 brick_id=self.brick_cls.id_, user=request.user,
#             )
#
#             try:
#                 if state.set_extra_data(key=BRICK_STATE_HIDE_INACTIVE_USERS, value=value):
#                     state.save()
#             except IntegrityError:
#                 logger.exception('Avoid a duplicate.')
#                 continue
#             else:
#                 break
#
#         return HttpResponse()
class HideInactiveUsers(BrickStateExtraDataSetting):
    brick_cls = UsersBrick
    data_key = BRICK_STATE_HIDE_INACTIVE_USERS
