# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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
from django.db import DatabaseError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _, ugettext

from creme.creme_core.auth.decorators import login_required, superuser_required, _check_superuser
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.models import lock
from creme.creme_core.views import generic
from creme.creme_core.views.decorators import POST_only

from ..forms import user as user_forms

# from .portal import _config_portal


logger = logging.getLogger(__name__)


# @login_required
# @superuser_required
# def change_password(request, user_id):
#     return generic.edit_model_with_popup(request, {'pk': user_id}, get_user_model(),
#                                          user_forms.UserChangePwForm,
#                                          _('Change password for «%s»'),
#                                         )
class PasswordChange(generic.CremeModelEditionPopup):
    model = get_user_model()
    form_class = user_forms.UserChangePwForm
    pk_url_kwarg = 'user_id'
    title_format = _('Change password for «{}»')

    def check_view_permissions(self, user):
        super().check_view_permissions(user=user)
        _check_superuser(user)


class BaseUserCreation(generic.CremeModelCreationPopup):
    model = get_user_model()

    def check_view_permissions(self, user):
        super().check_view_permissions(user=user)
        _check_superuser(user)


# @login_required
# @superuser_required
# def add(request):
#     return generic.add_model_with_popup(request, user_forms.UserAddForm)
class UserCreation(BaseUserCreation):
    form_class = user_forms.UserAddForm


# @login_required
# @superuser_required
# def add_team(request):
#     return generic.add_model_with_popup(request, user_forms.TeamCreateForm, _('New team'),
#                                         submit_label=_('Save the team'),
#                                        )
class TeamCreation(BaseUserCreation):
    form_class = user_forms.TeamCreateForm
    title = _('New team')
    submit_label = _('Save the team')


# @login_required
# def portal(request):
#     return _config_portal(request, 'creme_config/user_portal.html')
class Portal(generic.BricksView):
    template_name = 'creme_config/user_portal.html'


class BaseUserEdition(generic.CremeModelEditionPopup):
    model = get_user_model()
    pk_url_kwarg = 'user_id'

    def check_view_permissions(self, user):
        super().check_view_permissions(user=user)
        _check_superuser(user)

    def get_queryset(self):
        qs = super().get_queryset()

        return qs if self.request.user.is_staff else qs.filter(is_staff=False)


# @login_required
# @superuser_required
# def edit(request, user_id):
#     user_filter = {'pk':       user_id,
#                    'is_team':  False,
#                   }
#
#     if not request.user.is_staff:
#         user_filter['is_staff'] = False
#
#     return generic.edit_model_with_popup(request, user_filter, get_user_model(), user_forms.UserEditForm)
class UserEdition(BaseUserEdition):
    queryset = get_user_model().objects.filter(is_team=False)
    form_class = user_forms.UserEditForm


# @login_required
# @superuser_required
# def edit_team(request, user_id):
#     return generic.edit_model_with_popup(request,
#                                          {'pk':       user_id,
#                                           'is_team':  True,
#                                           'is_staff': False,
#                                          },
#                                          get_user_model(), user_forms.TeamEditForm,
#                                         )
class TeamEdition(BaseUserEdition):
    queryset = get_user_model().objects.filter(is_team=True, is_staff=False)
    form_class = user_forms.TeamEditForm


# @login_required
# @superuser_required
# def delete(request, user_id):
#     """Delete a User (who can be a Team). Objects linked to this User are
#     linked to a new User.
#     """
#     user = request.user
#
#     if int(user_id) == user.id:
#         raise ConflictError(ugettext("You can't delete the current user."))
#
#     user_to_delete = get_object_or_404(get_user_model(), pk=user_id)
#
#     if user_to_delete.is_staff and not user.is_staff:
#         return HttpResponse(ugettext("You can't delete a staff user."), status=400)
#
#     try:
#         return generic.add_model_with_popup(request, user_forms.UserAssignationForm,
#                                             _('Delete «{user}» and assign his entities to user').format(
#                                                     user=user_to_delete,
#                                                 ),
#                                             initial={'user_to_delete': user_to_delete},
#                                             submit_label=_('Delete the user'),
#                                            )
#     except Exception:
#         logger.exception('delete(): an error occurred')
#
#         return HttpResponse(_("You can't delete this user."), status=400)
class UserDeletion(BaseUserEdition):
    """View to delete a User (who can be a Team).

    Objects linked to this User are linked to another User
   (see forms.user.UserAssignationForm).
    """
    form_class = user_forms.UserAssignationForm
    template_name = 'creme_core/generics/blockform/delete_popup.html'
    title_format = _('Delete «{}» and assign his entities to user')
    submit_label = _('Delete the user')

    lock_name = 'creme_config-user_transfer'

    def get_object(self, *args, **kwargs):
        if int(self.kwargs[self.pk_url_kwarg]) == self.request.user.id:
            raise ConflictError(ugettext("You can't delete the current user."))

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


@login_required
@superuser_required
@POST_only
def deactivate(request, user_id):
    user = request.user

    if int(user_id) == user.id:
        raise ConflictError(ugettext("You can't deactivate the current user."))

    user_to_deactivate = get_object_or_404(get_user_model(), pk=user_id)

    if user_to_deactivate.is_staff and not user.is_staff:
        return HttpResponse(ugettext("You can't deactivate a staff user."), status=400)

    if user_to_deactivate.is_active:
        user_to_deactivate.is_active = False
        user_to_deactivate.save()

    return HttpResponse()


@login_required
@superuser_required
@POST_only
def activate(request, user_id):
    user_to_activate = get_object_or_404(get_user_model(), pk=user_id)

    if user_to_activate.is_staff and not request.user.is_staff:
        return HttpResponse(ugettext("You can't activate a staff user."), status=400)

    if not user_to_activate.is_active:
        user_to_activate.is_active = True
        user_to_activate.save()

    return HttpResponse()
