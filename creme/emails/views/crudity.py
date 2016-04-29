# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2016  Hybird
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

from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponse
from django.utils.translation import ugettext as _

from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.utils import jsonify
from creme.creme_core.views import blocks as blocks_views

from creme.crudity.views.actions import fetch

from .. import get_entityemail_model
from ..blocks import mail_waiting_sync_block, mail_spam_sync_block
from ..constants import (MAIL_STATUS_SYNCHRONIZED_SPAM,
        MAIL_STATUS_SYNCHRONIZED, MAIL_STATUS_SYNCHRONIZED_WAITING)


EntityEmail = get_entityemail_model()


# TODO: credentials (don't forget templates)
@login_required
@permission_required('emails')
def synchronisation(request):
    # TODO: Apply permissions?
    return fetch(request, template='emails/synchronize.html',
                 ajax_template='emails/frags/ajax/synchronize.html',
                 extra_tpl_ctx={
                        'entityemail_ct_id': ContentType.objects.get_for_model(EntityEmail).id,
                    }
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
        message = ",".join(errors)
        status = 400
    else:
        status = 200
        message = _(u'Operation successfully completed')

    return HttpResponse(message, content_type='text/javascript', status=status)


@login_required
@permission_required('emails')
def spam(request):
    return set_emails_status(request, MAIL_STATUS_SYNCHRONIZED_SPAM)


@login_required
@permission_required('emails')
def validated(request):
    return set_emails_status(request, MAIL_STATUS_SYNCHRONIZED)


@login_required
@permission_required('emails')
def waiting(request):
    return set_emails_status(request, MAIL_STATUS_SYNCHRONIZED_WAITING)


@jsonify
@permission_required('emails')
def reload_sync_blocks(request):
    ctx = blocks_views.build_context(request)

    return [(mail_waiting_sync_block.id_, mail_waiting_sync_block.detailview_display(ctx)),
            (mail_spam_sync_block.id_,    mail_spam_sync_block.detailview_display(ctx))
           ]
