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

from django.shortcuts import get_object_or_404  # render
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.utils import jsonify
from creme.creme_core.views import generic
from creme.creme_core.views.bricks import build_context, bricks_render_info
# from creme.creme_core.views.generic import add_to_entity

from .. import get_emailcampaign_model
from ..bricks import MailsBrick
from ..forms.sending import SendingCreateForm
from ..models import EmailSending


# @login_required
# @permission_required('emails')
# def add(request, campaign_id):
#     return add_to_entity(request, campaign_id, SendingCreateForm,
#                          _('New sending for «%s»'),
#                          entity_class=get_emailcampaign_model(),
#                          submit_label=EmailSending.save_label,
#                         )
class SendingCreation(generic.AddingToEntity):
    model = EmailSending
    form_class = SendingCreateForm
    entity_id_url_kwarg = 'campaign_id'
    entity_classes = get_emailcampaign_model()
    title_format = _('New sending for «{}»')


# TODO: used once => inline
def _get_sending(request, sending_id):
    sending  = get_object_or_404(EmailSending, pk=sending_id)
    campaign = sending.campaign

    request.user.has_perm_to_view_or_die(campaign)

    return sending


# @login_required
# @permission_required('emails')
# def detailview(request, sending_id):
#     return render(request, 'emails/popup_sending.html',
#                   context={'object': _get_sending(request, sending_id)},
#                  )
class LightWeightEmails(generic.RelatedToEntityDetail):
    model = EmailSending
    pk_url_kwarg = 'sending_id'
    permissions = 'emails'
    bricks_reload_url_name = 'emails__reload_lw_mails_brick'

    def get_brick_ids(self):
        return (
            MailsBrick.id_,
        )


# Useful method because EmailSending is not a CremeEntity (should be ?)
@login_required
@permission_required('emails')
@jsonify
def reload_mails_brick(request, sending_id):
    return bricks_render_info(
        request,
        bricks=[MailsBrick()],  # TODO: retrieve by 'id_' to allow complete overriding
        context=build_context(request, object=_get_sending(request, sending_id)),
    )
