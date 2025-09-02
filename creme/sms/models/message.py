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

from django.conf import settings
from django.db import models
from django.utils.formats import date_format
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext, pgettext_lazy

from creme.creme_core.models import CremeModel
from creme.creme_core.utils import chunktools, ellipsis

from ..webservice.backend import WSException
from ..webservice.samoussa import (
    SAMOUSSA_STATUS_ACCEPT,
    SAMOUSSA_STATUS_ERROR,
    SAMOUSSA_STATUS_SENT,
    SAMOUSSA_STATUS_WAITING,
    SamoussaBackEnd,
)

MESSAGE_STATUS_NOTSENT = 'notsent'
MESSAGE_STATUS_WAITING = SAMOUSSA_STATUS_WAITING
MESSAGE_STATUS_ACCEPT = SAMOUSSA_STATUS_ACCEPT
MESSAGE_STATUS_SENT = SAMOUSSA_STATUS_SENT
MESSAGE_STATUS_ERROR = SAMOUSSA_STATUS_ERROR

# TODO: can we manage plural in a better way ?
MESSAGE_STATUS = {
    MESSAGE_STATUS_NOTSENT: (
        pgettext_lazy('sms', 'Not sent'), pgettext_lazy('sms-plural', 'Not sent'),
    ),
    MESSAGE_STATUS_WAITING: (
        pgettext_lazy('sms', 'Waiting'),  pgettext_lazy('sms-plural', 'Waiting'),
    ),
    MESSAGE_STATUS_ACCEPT: (
        pgettext_lazy('sms', 'Accepted'), pgettext_lazy('sms-plural', 'Accepted'),
    ),
    MESSAGE_STATUS_SENT: (
        pgettext_lazy('sms', 'Sent'), pgettext_lazy('sms-plural', 'Sent'),
    ),
    MESSAGE_STATUS_ERROR: (_('Error'), _('Errors')),
}


class Sending(CremeModel):
    date = models.DateField(_('Date'), editable=False)
    campaign = models.ForeignKey(
        settings.SMS_CAMPAIGN_MODEL, on_delete=models.CASCADE,
        verbose_name=_('Related campaign'), related_name='sendings',
        editable=False,
    )
    template = models.ForeignKey(
        settings.SMS_TEMPLATE_MODEL,
        verbose_name=_('Message template'), on_delete=models.CASCADE,
        editable=False,
    )  # TODO: PROTECT ? copy data like in 'emails' ?
    content = models.TextField(_('Generated message'), max_length=160, editable=False)

    creation_label = pgettext_lazy('sms', 'Create a sending')
    save_label     = pgettext_lazy('sms', 'Save the sending')

    class Meta:
        app_label = 'sms'
        verbose_name = _('Sending')
        verbose_name_plural = _('Sendings')

    def __str__(self):
        return pgettext('sms', 'Sending of «{campaign}» on {date}').format(
            campaign=self.campaign,
            date=date_format(self.date, 'DATE_FORMAT'),
        )

    def delete(self, *args, **kwargs):
        ws = SamoussaBackEnd()  # TODO: 'with'
        ws.connect()
        ws.delete_messages(user_data=self.id)
        ws.close()

        return super().delete(*args, **kwargs)

    def formatstatus(self):
        # TODO: use <Conditional aggregation> to perform only one query
        items = (
            (self.messages.filter(status=status).count(), status_name)
            for status, status_name in MESSAGE_STATUS.items()
        )
        return ', '.join(
            f'{count} {label[1] if count > 1 else label[0]}'
            for count, label in items if count > 0
        )

    def get_related_entity(self):  # For generic views
        return self.campaign


# TODO: keep the related entity (to hide the number when the entity is not viewable)
class Message(CremeModel):
    sending = models.ForeignKey(
        Sending,
        verbose_name=_('Sending'), related_name='messages', on_delete=models.CASCADE,
    )
    phone = models.CharField(_('Number'), max_length=100)
    status = models.CharField(_('State'), max_length=10)
    status_message = models.CharField(_('Full state'), max_length=100, blank=True)

    def __str__(self):
        return self.phone

    class Meta:
        app_label = 'sms'
        verbose_name = pgettext_lazy('sms', 'Message')
        verbose_name_plural = pgettext_lazy('sms', 'Messages')

    # TODO: improve delete() method & remove the view delete_message ?
    # def get_related_entity(self):  # For generic views (deletion)
    #     return self.sending.campaign

    def statusname(self):
        status_desc = MESSAGE_STATUS.get(self.status)
        return status_desc[0] if status_desc else gettext('Unknown')

    @classmethod
    def _connect(cls, sending):
        ws = SamoussaBackEnd()

        try:
            ws.connect()
        except WSException as err:
            msg = ellipsis(
                str(err),
                length=cls._meta.get_field('status_message').max_length,
            )
            sending.messages.filter(status=MESSAGE_STATUS_NOTSENT).update(status_message=msg)
            return None

        return ws

    @staticmethod
    def _disconnect(ws):
        try:
            ws.close()
        except WSException:
            pass

    @classmethod
    def _do_action(cls, sending, request, action, step):
        ws = cls._connect(sending)

        if not ws:
            return

        # TODO: use FlowPaginator instead
        for chunk in chunktools.iter_as_slices(request, 256):
            action(ws, sending, chunk)

        cls._disconnect(ws)

    @classmethod
    def send(cls, sending):
        content = sending.content
        sending_id = sending.id
        messages = sending.messages.filter(
            status=MESSAGE_STATUS_NOTSENT,
        ).values_list('pk', 'phone')

        msg_mngr = cls._default_manager

        def action(ws, sending, chunk):
            pks = (m[0] for m in chunk)
            numbers = (m[1] for m in chunk)
            not_accepted = []

            try:
                res = ws.send_messages(content, [*numbers], sending_id)
                not_accepted = res.get('not_accepted', [])
            except WSException as err:
                msg_mngr.filter(pk__in=pks).update(status_message=str(err))

            for phone, status, status_message in not_accepted:
                msg_mngr.filter(
                    phone=phone, sending__id=sending_id,
                ).update(status=status, status_message=status_message)

            msg_mngr.filter(
                status=MESSAGE_STATUS_NOTSENT
            ).update(status=MESSAGE_STATUS_ACCEPT, status_message='')

        cls._do_action(sending, messages, action, 256)

    @classmethod
    def sync(cls, sending):
        sending_id = sending.id
        messages = sending.messages.values_list('pk', 'phone')

        def action(ws, sending, chunk):
            numbers = (m[1] for m in chunk)
            res = []

            try:
                res = ws.list_messages(
                    phone=[*numbers],
                    user_data=sending_id,
                    aslist=True,
                    fields=['phone', 'status', 'message'],
                )
            except WSException:
                pass

            for phone, status, status_message in res:
                cls._default_manager.filter(
                    phone=phone, sending__id=sending_id,
                ).update(status=status, status_message=status_message)

        cls._do_action(sending, messages, action, 256)

    def sync_delete(self):
        ws = SamoussaBackEnd()

        try:
            ws.connect()
            ws.delete_message(self)

            self.status = MESSAGE_STATUS_NOTSENT
            self.save(force_update=True)

            ws.close()
        except WSException:
            pass

    sync_delete.alters_data = True


# TODO : enable this method when samoussa will be updated
#    @staticmethod
#    def syncs(request):
#        messages = {str(message.pk) + '-' + str(message.sending_id): message
#                        for message in request
#                   }
#        samoussa = SamoussaBackEnd().connect()
#
#        for entry in samoussa.messages(user_data=messages.iterkeys()):
#            message = messages.get(entry.get('user_data'))
#            message.status = entry.get('status')
#            message.status_message = entry.get('status_message')
#            message.save()
