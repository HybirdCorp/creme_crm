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

# from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.shortcuts import render
from django.utils.translation import ugettext as _

from creme.creme_core.auth.decorators import login_required, permission_required
# from creme.creme_core.utils import jsonify

from creme.crudity import registry

from .. import bricks, constants, get_entityemail_model
from ..crudity_register import EntityEmailBackend


EntityEmail = get_entityemail_model()


# TODO: credentials (don't forget templates)
@login_required
@permission_required('emails')
def synchronisation(request):
    # TODO: Apply permissions?
    bricks_obj = None

    try:
        backend = registry.crudity_registry.get_default_backend('email')
    except KeyError:
        pass
    else:
        if isinstance(backend, EntityEmailBackend):
            bricks_obj = [bricks.WaitingSynchronizationMailsBrick(backend=backend),
                          bricks.SpamSynchronizationMailsBrick(backend=backend),
                         ]

    return render(request, template_name='emails/synchronize.html',
                  context={'bricks':            bricks_obj,
                           'bricks_reload_url': reverse('crudity__reload_actions_bricks'),
                           # 'entityemail_ct_id': ContentType.objects.get_for_model(EntityEmail).id,
                          },
                 )


def set_emails_status(request, status):
    user = request.user
    errors = []
    has_perm = user.has_perm_to_change

    for email in EntityEmail.objects.filter(id__in=request.POST.getlist('ids')):
        if not has_perm(email):
            errors.append(_(u'You are not allowed to edit this entity: %s') %
                            email.allowed_unicode(user)
                         )
        else:
            email.status = status
            email.save()

    if errors:
        message = ','.join(errors)
        status = 400
    else:
        status = 200
        message = _(u'Operation successfully completed')

    return HttpResponse(message, content_type='text/javascript', status=status)


@login_required
@permission_required('emails')
def spam(request):
    return set_emails_status(request, constants.MAIL_STATUS_SYNCHRONIZED_SPAM)


@login_required
@permission_required('emails')
def validated(request):
    return set_emails_status(request, constants.MAIL_STATUS_SYNCHRONIZED)


@login_required
@permission_required('emails')
def waiting(request):
    return set_emails_status(request, constants.MAIL_STATUS_SYNCHRONIZED_WAITING)


# @jsonify
# @permission_required('emails')
# def reload_sync_blocks(request):
#     warnings.warn('emails.views.crudity.reload_sync_blocks() is deprecated ; use reload_bricks() instead.',
#                   DeprecationWarning
#                  )
#
#     from creme.creme_core.views.blocks import build_context
#     from .. import blocks
#
#     ctx = build_context(request)
#     mail_waiting_sync_block = blocks.WaitingSynchronizationMailsBlock()
#     mail_spam_sync_block    = blocks.SpamSynchronizationMailsBlock()
#
#     return [(mail_waiting_sync_block.id_, mail_waiting_sync_block.detailview_display(ctx)),
#             (mail_spam_sync_block.id_,    mail_spam_sync_block.detailview_display(ctx)),
#            ]
