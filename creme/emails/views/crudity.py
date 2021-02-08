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

# import warnings
from django.core.exceptions import PermissionDenied
from django.db.transaction import atomic
from django.http import Http404, HttpResponse
from django.utils.translation import gettext as _

# from creme.creme_core.auth import decorators
from creme.creme_core.views import generic
from creme.crudity import registry

from .. import bricks, get_entityemail_model  # constants
from ..crudity_register import EntityEmailBackend

EntityEmail = get_entityemail_model()


# TODO: credentials (don't forget templates)
class Synchronisation(generic.BricksView):
    template_name = 'emails/synchronize.html'
    permissions = 'emails'
    bricks_reload_url_name = 'crudity__reload_actions_bricks'

    def get_bricks(self):
        # TODO: Apply permissions?
        bricks_obj = None

        try:
            backend = registry.crudity_registry.get_default_backend('email')
        except KeyError:
            pass
        else:
            if isinstance(backend, EntityEmailBackend):
                bricks_obj = [
                    bricks.WaitingSynchronizationMailsBrick(backend=backend),
                    bricks.SpamSynchronizationMailsBrick(backend=backend),
                ]

        return bricks_obj


# @decorators.login_required
# @decorators.permission_required('emails')
# def set_emails_status(request, status):
#     warnings.warn('emails.views.crudity.set_emails_status() is deprecated.',
#                   DeprecationWarning
#                  )
#
#     user = request.user
#     errors = []
#     has_perm_or_die = user.has_perm_to_change_or_die
#
#     with atomic():
#         for email in EntityEmail.objects.filter(id__in=request.POST.getlist('ids')) \
#                                         .select_for_update():
#             try:
#                 has_perm_or_die(email)
#             except PermissionDenied as e:
#                 errors.append(str(e))
#             else:
#                 email.status = status
#                 email.save()
#
#     if errors:
#         message = ','.join(errors)
#         status = 400
#     else:
#         status = 200
#         message = _('Operation successfully completed')
#
#     return HttpResponse(message, status=status)


# def spam(request):
#     warnings.warn('emails.views.crudity.spam() is deprecated ; '
#                   'use EmailStatusSetting instead.',
#                   DeprecationWarning
#                  )
#
#     return set_emails_status(request, constants.MAIL_STATUS_SYNCHRONIZED_SPAM)


# def validated(request):
#     warnings.warn('emails.views.crudity.validated() is deprecated ; '
#                   'use EmailStatusSetting instead.',
#                   DeprecationWarning
#                  )
#
#     return set_emails_status(request, constants.MAIL_STATUS_SYNCHRONIZED)


# def waiting(request):
#     warnings.warn('emails.views.crudity.waiting() is deprecated ; '
#                   'use EmailStatusSetting instead.',
#                   DeprecationWarning
#                  )
#
#     return set_emails_status(request, constants.MAIL_STATUS_SYNCHRONIZED_WAITING)


class EmailStatusSetting(generic.CheckedView):
    permissions = 'emails'
    model = EntityEmail
    status_url_kwarg = 'status'
    status_map = {
        # 'validated': constants.MAIL_STATUS_SYNCHRONIZED,
        # 'spam':      constants.MAIL_STATUS_SYNCHRONIZED_SPAM,
        # 'waiting':   constants.MAIL_STATUS_SYNCHRONIZED_WAITING,
        'validated': EntityEmail.Status.SYNCHRONIZED,
        'spam':      EntityEmail.Status.SYNCHRONIZED_SPAM,
        'waiting':   EntityEmail.Status.SYNCHRONIZED_WAITING,
    }
    email_ids_arg = 'ids'

    def get_email_status(self):
        try:
            return self.status_map[self.kwargs[self.status_url_kwarg]]
        except KeyError as e:
            raise Http404(f'Invalid status: {e}') from e

    def post(self, request, **kwargs):
        email_status = self.get_email_status()
        user = request.user
        errors = []
        has_perm_or_die = user.has_perm_to_change_or_die

        with atomic():
            for email in self.model.objects.filter(
                id__in=request.POST.getlist(self.email_ids_arg),
            ).select_for_update():
                try:
                    has_perm_or_die(email)
                except PermissionDenied as e:
                    errors.append(str(e))
                else:
                    email.status = email_status
                    email.save()

        if errors:
            message = ','.join(errors)
            status = 400
        else:
            status = 200
            message = _('Operation successfully completed')

        return HttpResponse(message, status=status)
