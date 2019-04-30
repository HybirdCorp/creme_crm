# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2019  Hybird
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

from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _

from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.utils.html import sanitize_html
from creme.creme_core.views import generic, bricks as bricks_views
from creme.creme_core.views.decorators import jsonify

from .. import get_emailcampaign_model
from ..bricks import MailsBrick, SendingBrick, SendingHTMLBodyBrick
from ..forms.sending import SendingCreateForm
from ..models import EmailSending


class SendingCreation(generic.AddingInstanceToEntityPopup):
    model = EmailSending
    form_class = SendingCreateForm
    entity_id_url_kwarg = 'campaign_id'
    entity_classes = get_emailcampaign_model()
    title = _('New sending for «{entity}»')


# def _get_sending(request, sending_id):
#     warnings.warn('emails.views.sending._get_sending() is deprecated.',
#                   DeprecationWarning
#                  )
#
#     sending  = get_object_or_404(EmailSending, pk=sending_id)
#     campaign = sending.campaign
#
#     request.user.has_perm_to_view_or_die(campaign)
#
#     return sending


class SendingDetail(generic.RelatedToEntityDetail):
    model = EmailSending
    template_name = 'emails/view_sending.html'
    pk_url_kwarg = 'sending_id'
    permissions = 'emails'
    bricks_reload_url_name = 'emails__reload_sending_bricks'


# TODO: factorise with get_lightweight_mail_body()
class SendingBody(generic.RelatedToEntityDetail):
    model = EmailSending
    pk_url_kwarg = 'sending_id'
    permissions = 'emails'

    def render_to_response(self, context, **response_kwargs):
        return HttpResponse(
            sanitize_html(self.object.body_html,
                          # TODO: ? allow_external_img=request.GET.get('external_img', False),
                          allow_external_img=True,
                         )
        )


# @login_required
# @permission_required('emails')
# @jsonify
# def reload_mails_brick(request, sending_id):
#     warnings.warn('emails.views.sending.reload_mails_brick() is deprecated ; '
#                   'use reload_sending_bricks() instead.',
#                   DeprecationWarning
#                  )
#     return bricks_views.bricks_render_info(
#         request,
#         bricks=[MailsBrick()],
#         context=bricks_views.build_context(request, object=_get_sending(request, sending_id)),
#     )


# Useful method because EmailSending is not a CremeEntity (should be ?)
@login_required
@permission_required('emails')
@jsonify
def reload_sending_bricks(request, sending_id):
    sending = get_object_or_404(EmailSending, pk=sending_id)
    request.user.has_perm_to_view_or_die(sending.campaign)

    bricks = []
    allowed_bricks = {
        SendingBrick.id_:         SendingBrick,
        SendingHTMLBodyBrick.id_: SendingHTMLBodyBrick,
        MailsBrick.id_:           MailsBrick,
    }

    for brick_id in bricks_views.get_brick_ids_or_404(request):
        brick_cls = allowed_bricks.get(brick_id)

        if brick_cls is not None:
            bricks.append(brick_cls())
        else:
            raise Http404('Invalid brick ID')

    return bricks_views.bricks_render_info(
        request,
        bricks=bricks,
        context=bricks_views.build_context(request, object=sending),
    )
