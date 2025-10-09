################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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

from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import gettext_lazy as _

from creme.creme_core.auth.decorators import (
    login_required,
    permission_required,
)
from creme.creme_core.http import is_ajax
from creme.creme_core.utils import get_from_POST_or_404
from creme.creme_core.views import generic
from creme.creme_core.views.bricks import BricksReloading

from .. import get_smscampaign_model
from ..bricks import MessagesBrick
from ..forms.message import SendingCreationForm
from ..models import Message, Sending


class SendingCreation(generic.AddingInstanceToEntityPopup):
    model = Sending
    form_class = SendingCreationForm
    entity_id_url_kwarg = 'campaign_id'
    entity_classes = get_smscampaign_model()
    title = _('New sending for «{entity}»')


# TODO: use 'creme_core__delete_related_to_entity' instead ?
@login_required
@permission_required('sms')
def delete(request):
    sending  = get_object_or_404(Sending, id=get_from_POST_or_404(request.POST, 'id'))
    campaign = sending.campaign

    request.user.has_perm_to_change_or_die(campaign)

    sending.delete()  # TODO: try/except ??

    if is_ajax(request):
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


# TODO: RelatedToEntityDetail when Sending is/if an auxiliary
class Messages(generic.CremeModelDetailPopup):
    model = Sending
    pk_url_kwarg = 'id'
    permissions = 'sms'
    bricks_reload_url_name = 'sms__reload_messages_brick'
    bricks = [MessagesBrick]

    def check_instance_permissions(self, instance, user):
        user.has_perm_to_view_or_die(instance.campaign)

    def get_bricks(self):
        # return [MessagesBrick()]
        return {'main': [brick_cls() for brick_cls in self.bricks]}


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

    if is_ajax(request):
        return HttpResponse('success')  # TODO: no message, status is OK...

    return redirect(campaign)


class MessagesBrickReloading(BricksReloading):
    permissions = 'sms'
    sending_id_url_kwarg = 'sending_id'
    bricks = Messages.bricks

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.sending = None

    def get_bricks(self):
        # return [MessagesBrick()]
        bricks = []
        allowed_bricks = {brick_cls.id: brick_cls for brick_cls in self.bricks}

        for brick_id in self.get_brick_ids():
            try:
                brick_cls = allowed_bricks[brick_id]
            except KeyError as e:
                raise Http404('Invalid brick ID') from e

            bricks.append(brick_cls())

        return bricks

    def get_bricks_context(self):
        context = super().get_bricks_context()
        context['object'] = self.get_sending()

        return context

    def get_sending(self):
        sending = self.sending

        if sending is None:
            self.sending = sending = get_object_or_404(
                Sending,
                id=self.kwargs[self.sending_id_url_kwarg],
            )
            self.request.user.has_perm_to_view_or_die(sending.campaign)

        return sending
