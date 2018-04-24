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

from django.conf import settings
from django.db.models import ForeignKey, CharField, DateField, TextField, CASCADE
from django.utils.formats import date_format
from django.utils.translation import ugettext_lazy as _, ugettext, pgettext, pgettext_lazy

from creme.creme_core.models import CremeModel
from creme.creme_core.utils import chunktools

from ..webservice.samoussa import (SamoussaBackEnd, SAMOUSSA_STATUS_ACCEPT,
        SAMOUSSA_STATUS_WAITING, SAMOUSSA_STATUS_SENT,
        SAMOUSSA_STATUS_ERROR)
from ..webservice.backend import WSException


MESSAGE_STATUS_NOTSENT = 'notsent'
MESSAGE_STATUS_WAITING = SAMOUSSA_STATUS_WAITING
MESSAGE_STATUS_ACCEPT = SAMOUSSA_STATUS_ACCEPT
MESSAGE_STATUS_SENT = SAMOUSSA_STATUS_SENT
MESSAGE_STATUS_ERROR = SAMOUSSA_STATUS_ERROR

# TODO: can we manage plural in a better way ?
MESSAGE_STATUS = {
    MESSAGE_STATUS_NOTSENT: (pgettext_lazy('sms', u'Not sent'), pgettext_lazy('sms-plural', u'Not sent')),
    MESSAGE_STATUS_WAITING: (pgettext_lazy('sms', u'Waiting'),  pgettext_lazy('sms-plural', u'Waiting')),
    MESSAGE_STATUS_ACCEPT:  (pgettext_lazy('sms', u'Accepted'), pgettext_lazy('sms-plural', u'Accepted')),
    MESSAGE_STATUS_SENT:    (pgettext_lazy('sms', u'Sent'),     pgettext_lazy('sms-plural', u'Sent')),
    MESSAGE_STATUS_ERROR:   (_(u'Error'),                       _(u'Errors')),
}


class Sending(CremeModel):
    date     = DateField(_(u'Date'))
    campaign = ForeignKey(settings.SMS_CAMPAIGN_MODEL, on_delete=CASCADE,
                          verbose_name=_(u'Related campaign'), related_name='sendings',
                         )
    template = ForeignKey(settings.SMS_TEMPLATE_MODEL, verbose_name=_(u'Message template'), on_delete=CASCADE)  # TODO: PROTECT ? copy data like in 'emails' ?
    content  = TextField(_(u'Generated message'), max_length=160)

    creation_label = pgettext_lazy('sms', u'Create a sending')
    save_label     = pgettext_lazy('sms', u'Save the sending')

    class Meta:
        app_label = 'sms'
        verbose_name = _(u'Sending')
        verbose_name_plural = _(u'Sendings')

    def __unicode__(self):
        # return self.date
        return pgettext('sms', u'Sending of «{campaign}» on {date}').format(
                    campaign=self.campaign,
                    date=date_format(self.date, 'DATE_FORMAT'),
               )

    def formatstatus(self):
        items = ((self.messages.filter(status=status).count(), status_name) for status, status_name in MESSAGE_STATUS.iteritems())
        return ', '.join((u'%s %s' % (count, label[1] if count > 1 else label[0]) for count, label in items if count > 0))

    # def delete(self, using=None):
    def delete(self, *args, **kwargs):
        ws = SamoussaBackEnd()  # TODO: 'with'
        ws.connect()
        ws.delete_messages(user_data=self.id)
        ws.close()

        # self.messages.all().delete()
        # return super(Sending, self).delete(using=using)
        return super(Sending, self).delete(*args, **kwargs)


# TODO: keep the related entity (to hide the number when the entity is not viewable)
class Message(CremeModel):
    sending = ForeignKey(Sending, verbose_name=_(u'Sending'), related_name='messages', on_delete=CASCADE)
    phone  = CharField(_(u'Number'), max_length=100)
    status = CharField(_(u'State'), max_length=10)
    status_message = CharField(_(u'Full state'), max_length=100, blank=True)

    def __unicode__(self):
        return self.phone

    class Meta:
        app_label = 'sms'
        verbose_name = _(u'Message')
        verbose_name_plural = _(u'Messages')

    # TODO: improve delete() method & remove the view delete_message ?
    # def get_related_entity(self):  # For generic views (deletion)
    #     return self.sending.campaign

    def statusname(self):
        status_desc = MESSAGE_STATUS.get(self.status)
        return status_desc[0] if status_desc else ugettext(u'Unknown')

    @staticmethod
    def _connect(sending):
        ws = SamoussaBackEnd()

        try:
            ws.connect()
        except WSException as err:
            sending.messages.filter(status=MESSAGE_STATUS_NOTSENT).update(status_message=unicode(err))
            return None

        return ws

    @staticmethod
    def _disconnect(ws):
        try:
            ws.close()
        except WSException:
            pass

    @staticmethod
    def _do_action(sending, request, action, step):
        ws = Message._connect(sending)

        if not ws:
            return

        # TODO: use FlowPaginator instead
        for chunk in chunktools.iter_as_slices(request, 256):
            action(ws, sending, chunk)

        Message._disconnect(ws)

    @staticmethod
    def send(sending):
        content = sending.content
        sending_id = sending.id
        messages = sending.messages.filter(status=MESSAGE_STATUS_NOTSENT).values_list('pk', 'phone')

        def action(ws, sending, chunk):
            pks = (m[0] for m in chunk)
            numbers = (m[1] for m in chunk)
            not_accepted = []

            try:
                res = ws.send_messages(content, list(numbers), sending_id)
                not_accepted = res.get('not_accepted', [])
            except WSException as err:
                Message.objects.filter(pk__in=pks).update(status_message=unicode(err))

            for phone, status, status_message in not_accepted:
                Message.objects.filter(phone=phone, sending__id=sending_id) \
                               .update(status=status, status_message=status_message)

            Message.objects.filter(status=MESSAGE_STATUS_NOTSENT) \
                           .update(status=MESSAGE_STATUS_ACCEPT, status_message='')

        Message._do_action(sending, messages, action, 256)

    @staticmethod
    def sync(sending):
        sending_id = sending.id
        messages = sending.messages.values_list('pk', 'phone')

        def action(ws, sending, chunk):
            numbers = (m[1] for m in chunk)
            res = []

            try:
                res = ws.list_messages(phone=list(numbers), user_data=sending_id,
                                       aslist=True, fields=['phone', 'status', 'message'],
                                      )
            except WSException:
                pass

            # print res

            for phone, status, status_message in res:
                Message.objects.filter(phone=phone, sending__id=sending_id) \
                               .update(status=status, status_message=status_message)

        Message._do_action(sending, messages, action, 256)

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
