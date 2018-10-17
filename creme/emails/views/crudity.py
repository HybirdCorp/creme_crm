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

# import warnings

from django.core.exceptions import PermissionDenied
from django.db.transaction import atomic
from django.http import HttpResponse
# from django.shortcuts import render
# from django.urls import reverse
from django.utils.translation import ugettext as _

from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.views.generic import BricksView

from creme.crudity import registry

from .. import bricks, constants, get_entityemail_model
from ..crudity_register import EntityEmailBackend


EntityEmail = get_entityemail_model()


# TODO: credentials (don't forget templates)
# @login_required
# @permission_required('emails')
# def synchronisation(request):
#     # todo: Apply permissions?
#     bricks_obj = None
#
#     try:
#         backend = registry.crudity_registry.get_default_backend('email')
#     except KeyError:
#         pass
#     else:
#         if isinstance(backend, EntityEmailBackend):
#             bricks_obj = [bricks.WaitingSynchronizationMailsBrick(backend=backend),
#                           bricks.SpamSynchronizationMailsBrick(backend=backend),
#                          ]
#
#     return render(request, template_name='emails/synchronize.html',
#                   context={'bricks':            bricks_obj,
#                            'bricks_reload_url': reverse('crudity__reload_actions_bricks'),
#                           },
#                  )
class Synchronisation(BricksView):
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


@login_required
@permission_required('emails')
def set_emails_status(request, status):
    user = request.user
    errors = []
    # has_perm = user.has_perm_to_change
    has_perm_or_die = user.has_perm_to_change_or_die

    with atomic():
        for email in EntityEmail.objects.filter(id__in=request.POST.getlist('ids')) \
                                        .select_for_update():
            # if not has_perm(email):
            #     errors.append(_('You are not allowed to edit this entity: {}').format(
            #                     email.allowed_str(user)
            #                  ))
            # else:
            #     email.status = status
            #     email.save()
            try:
                has_perm_or_die(email)
            except PermissionDenied as e:
                errors.append(str(e))
            else:
                email.status = status
                email.save()

    if errors:
        message = ','.join(errors)
        status = 400
    else:
        status = 200
        message = _('Operation successfully completed')

    return HttpResponse(message, status=status)


def spam(request):
    return set_emails_status(request, constants.MAIL_STATUS_SYNCHRONIZED_SPAM)


def validated(request):
    return set_emails_status(request, constants.MAIL_STATUS_SYNCHRONIZED)


def waiting(request):
    return set_emails_status(request, constants.MAIL_STATUS_SYNCHRONIZED_WAITING)
