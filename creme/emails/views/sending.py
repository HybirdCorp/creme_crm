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
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.utils.formats import date_format
from django.utils.timezone import localtime
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy
from django.views.decorators.clickjacking import xframe_options_sameorigin

import creme.creme_core.views.bricks as bricks_views
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.utils import get_from_POST_or_404
from creme.creme_core.utils.html import sanitize_html
from creme.creme_core.views import generic

from .. import bricks, get_emailcampaign_model
from ..forms import sending as sending_forms
from ..models import EmailSending, EmailSendingConfigItem


class SendingConfigItemCreation(generic.CremeModelCreationPopup):
    model = EmailSendingConfigItem
    form_class = sending_forms.SendingConfigItemCreationForm
    permissions = 'emails.can_admin'


class SendingConfigItemEdition(generic.CremeModelEditionPopup):
    model = EmailSendingConfigItem
    form_class = sending_forms.SendingConfigItemEditionForm
    pk_url_kwarg = 'item_id'
    title = pgettext_lazy('emails', 'Edit the server configuration')
    submit_label = EmailSendingConfigItem.save_label
    permissions = 'emails.can_admin'


class SendingConfigItemPasswordEdition(generic.CremeModelEditionPopup):
    model = EmailSendingConfigItem
    form_class = sending_forms.SendingConfigItemPasswordEditionForm
    pk_url_kwarg = 'item_id'
    title = pgettext_lazy('emails', 'Edit the server password')
    submit_label = _('Save the password')
    permissions = 'emails.can_admin'


class SendingConfigItemDeletion(generic.CheckedView):
    id_arg = 'id'
    permissions = 'emails.can_admin'

    def post(self, request, **kwargs):
        get_object_or_404(
            EmailSendingConfigItem,
            pk=get_from_POST_or_404(request.POST, self.id_arg),
        ).delete()

        return HttpResponse()


class SendingCreation(generic.AddingInstanceToEntityPopup):
    model = EmailSending
    form_class = sending_forms.SendingCreationForm
    entity_id_url_kwarg = 'campaign_id'
    entity_classes = get_emailcampaign_model()
    title = _('New sending for «{entity}»')


class SendingEdition(generic.RelatedToEntityEditionPopup):
    model = EmailSending
    form_class = sending_forms.SendingEditionForm
    pk_url_kwarg = 'sending_id'
    title = _('Edit the sending on {date}')

    def check_instance_permissions(self, instance, user):
        if instance.state == EmailSending.State.DONE:
            raise ConflictError(gettext('This sending is done.'))

    def get_title_format_data(self):
        data = super().get_title_format_data()
        data['date'] = date_format(
            value=localtime(self.object.sending_date),
            format='DATETIME_FORMAT',
        )

        return data


class SendingDetail(generic.RelatedToEntityDetail):
    model = EmailSending
    template_name = 'emails/view_sending.html'
    pk_url_kwarg = 'sending_id'
    permissions = 'emails'
    bricks_reload_url_name = 'emails__reload_sending_bricks'
    bricks = {
        'top': [],
        'left': [bricks.SendingBrick, bricks.SendingHTMLBodyBrick],
        'right': [bricks.MailsBrick],
        'bottom': [],
    }

    def get_bricks(self):
        return {
            zone: [brick_class() for brick_class in brick_classes]
            for zone, brick_classes in self.bricks.items()
        }


# TODO: factorise with get_lightweight_mail_body()
@method_decorator(xframe_options_sameorigin, name='dispatch')
class SendingBody(generic.RelatedToEntityDetail):
    model = EmailSending
    pk_url_kwarg = 'sending_id'
    permissions = 'emails'

    def render_to_response(self, context, **response_kwargs):
        return HttpResponse(
            sanitize_html(
                self.object.body_html,
                # TODO: ? allow_external_img=request.GET.get('external_img', False),
                allow_external_img=True,
            )
        )


# Useful because EmailSending is not a CremeEntity (should be ?)
class SendingBricksReloading(bricks_views.BricksReloading):
    permissions = 'emails'
    # check_bricks_permission = False
    sending_id_url_kwarg = 'sending_id'
    # allowed_bricks = {
    #     bricks.SendingBrick.id:         bricks.SendingBrick,
    #     bricks.SendingHTMLBodyBrick.id: bricks.SendingHTMLBodyBrick,
    #     bricks.MailsBrick.id:           bricks.MailsBrick,
    # }
    bricks = SendingDetail.bricks

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.sending = None

    def get_bricks(self):
        bricks = []
        # allowed_bricks = self.allowed_bricks
        allowed_bricks = {
            brick_cls.id: brick_cls
            for brick_classes in self.bricks.values()
            for brick_cls in brick_classes
        }

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
                EmailSending,
                pk=self.kwargs[self.sending_id_url_kwarg],
            )
            self.request.user.has_perm_to_view_or_die(sending.campaign)

        return sending
