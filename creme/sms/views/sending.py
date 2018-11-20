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

from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect  # render
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.utils import get_from_POST_or_404, jsonify
from creme.creme_core.views.bricks import build_context, bricks_render_info
# from creme.creme_core.views.generic import add_to_entity
from creme.creme_core.views import generic

from .. import get_smscampaign_model
from ..bricks import MessagesBrick
from ..forms.message import SendingCreateForm
from ..models import Sending, Message
# from creme.sms.webservice.samoussa import SamoussaBackEnd
# from creme.sms.webservice.backend import WSException


# @login_required
# @permission_required('sms')
# def add(request,campaign_id):
#     return add_to_entity(request, campaign_id, SendingCreateForm,
#                          _(u'New sending for «%s»'),
#                          entity_class=get_smscampaign_model(),
#                          submit_label=Sending.save_label,
#                         )
class SendingCreation(generic.AddingInstanceToEntityPopup):
    model = Sending
    form_class = SendingCreateForm
    entity_id_url_kwarg = 'campaign_id'
    entity_classes = get_smscampaign_model()
    title_format = _('New sending for «{}»')


# TODO: use 'creme_core__delete_related_to_entity' instead ?
@login_required
@permission_required('sms')
def delete(request):
    sending  = get_object_or_404(Sending, id=get_from_POST_or_404(request.POST, 'id'))
    campaign = sending.campaign

    request.user.has_perm_to_change_or_die(campaign)

    sending.delete()  # TODO: try/except ??

    if request.is_ajax():
        return HttpResponse('success')  # TODO: no message, status is OK...

    return redirect(campaign)


@login_required
@permission_required('sms')
def sync_messages(request, id):
    sending = get_object_or_404(Sending, id=id)
    request.user.has_perm_to_change_or_die(sending.campaign)

    Message.sync(sending)

    return HttpResponse()


@login_required
@permission_required('sms')
def send_messages(request, id):
    sending = get_object_or_404(Sending, id=id)
    request.user.has_perm_to_change_or_die(sending.campaign)

    Message.send(sending)

    return HttpResponse()


# @login_required
# @permission_required('sms')
# def detailview(request, id):
#     sending = get_object_or_404(Sending, id=id)
#     request.user.has_perm_to_view_or_die(sending.campaign)
#
#     return render(request, 'sms/popup_sending.html', {'object': sending})
# TODO: RelatedToEntityDetail when Sending is/if an auxiliary
class Messages(generic.CremeModelDetailPopup):
    model = Sending
    # template_name = 'sms/popup_sending.html'
    pk_url_kwarg = 'id'
    permissions = 'sms'
    bricks_reload_url_name = 'sms__reload_messages_brick'

    def check_instance_permissions(self, instance, user):
        user.has_perm_to_view_or_die(instance.campaign)

    def get_brick_ids(self):
        return (
            MessagesBrick.id_,
        )


# TODO: improve Message.delete() instead ?
@login_required
@permission_required('sms')
def delete_message(request):
    message  = get_object_or_404(Message, id=get_from_POST_or_404(request.POST, 'id'))
    campaign = message.sending.campaign

    request.user.has_perm_to_change_or_die(campaign)

    try:
        message.sync_delete()
        message.delete()
    except Exception as e:
        return HttpResponse(e, status=500)  # TODO: WTF ?!

    if request.is_ajax():
        return HttpResponse('success')  # TODO: no message, status is OK...

    return redirect(campaign)


@login_required
@permission_required('sms')
@jsonify
def reload_messages_brick(request, id):
    # TODO: factorise
    sending = get_object_or_404(Sending, id=id)
    request.user.has_perm_to_view_or_die(sending.campaign)

    return bricks_render_info(
        request,
        bricks=[MessagesBrick()],  # TODO: retrieve by 'id_' to allow complete overriding
        context=build_context(request, object=sending),
    )
