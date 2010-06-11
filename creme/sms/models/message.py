# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

from django.db.models import ForeignKey, CharField, DateField, TextField
from django.db.models.aggregates import Count
from django.utils.translation import ugettext as _

from creme_core.models import CremeModel
from creme_core.utils import chunktools

from sms.models.campaign import SMSCampaign
from sms.models.template import MessageTemplate

from sms.webservice.samoussa import (SamoussaBackEnd, 
                                     SAMOUSSA_STATUS_ACCEPT, 
                                     SAMOUSSA_STATUS_WAITING, 
                                     SAMOUSSA_STATUS_SENT,
                                     SAMOUSSA_STATUS_ERROR,)
from sms.webservice.backend import WSException



MESSAGE_STATUS_NOTSENT = 'notsent'
MESSAGE_STATUS_WAITING = SAMOUSSA_STATUS_WAITING
MESSAGE_STATUS_ACCEPT = SAMOUSSA_STATUS_ACCEPT
MESSAGE_STATUS_SENT = SAMOUSSA_STATUS_SENT
MESSAGE_STATUS_ERROR = SAMOUSSA_STATUS_ERROR

MESSAGE_STATUS_TRADS = {MESSAGE_STATUS_NOTSENT:(_(u'Non envoyé'), _(u'Non envoyés')),
                        MESSAGE_STATUS_WAITING:(_(u'En attente'), _(u'En attente')),
                        MESSAGE_STATUS_ACCEPT:(_(u'Accepté'), _(u'Acceptés')),
                        MESSAGE_STATUS_SENT:(_(u'Envoyé'), _(u'Envoyés')),
                        MESSAGE_STATUS_ERROR:(_(u'Erreur'), _(u'Erreurs'))}


class Sending(CremeModel):
    class Meta:
        app_label = "sms"
        verbose_name = _(u'Envoi')
        verbose_name_plural = _(u'Envois')

    date = DateField()
    campaign = ForeignKey(SMSCampaign, verbose_name=_(u'Campagne'), related_name="sendings")
    template = ForeignKey(MessageTemplate, verbose_name=_(u'Patron de message'))
    content = TextField(_(u'Message généré'), max_length=160)
        
    def __unicode__(self):
        return self.date
    
    def formatstatus(self):
        items = ((self.messages.filter(status=status).count(), status_name) for status, status_name in MESSAGE_STATUS_TRADS.iteritems())
        return ', '.join(('%s %s' % (count, label[1] if count > 1 else label[0]) for count, label in items if count > 0))

    def delete(self):
        ws = SamoussaBackEnd()
        ws.connect()
        ws.delete_messages(user_data=self.id)
        ws.close()
        
        self.messages.all().delete()
        return super(Sending, self).delete()


class Message(CremeModel):
    sending = ForeignKey(Sending, verbose_name=_(u'Envoi'), related_name='messages')
    phone  = CharField(_(u'Numéro'), max_length=100)
    status = CharField(_(u'État'), max_length=10)
    status_message = CharField(_(u'État détaillé'), max_length=100, blank=True, null=True)

    def __unicode__(self):
        return self.phone

    class Meta:
        app_label = "sms"
        verbose_name = _(u'Message')
        verbose_name_plural = _(u'Messages')

    def statusname(self):
        return MESSAGE_STATUS_TRADS.get(self.status, _(u'Inconnu'))[0]

    @staticmethod
    def _connect(sending):
        ws = SamoussaBackEnd()
        
        try:
            ws.connect()
        except WSException, err:
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
            
            #print 'send action', chunk
            
            try:
                res = ws.send_messages(content, list(numbers), sending_id)
                not_accepted = res.get('not_accepted', [])
            except WSException, err:
                Message.objects.filter(pk__in=pks).update(status_message=unicode(err)) 

            for phone, status, status_message in not_accepted:
                Message.objects.filter(phone=phone, sending__id=sending_id).update(status=status, 
                                                                                   status_message=status_message)
            
            Message.objects.filter(status=MESSAGE_STATUS_NOTSENT).update(status=MESSAGE_STATUS_ACCEPT, status_message='')
        
        Message._do_action(sending, messages, action, 256)

    @staticmethod
    def sync(sending):
        sending_id = sending.id
        messages = sending.messages.values_list('pk', 'phone')
        
        def action(ws, sending, chunk):
            numbers = (m[1] for m in chunk)
            res = []
            
            try:
                res = ws.list_messages(phone=list(numbers), user_data=sending_id, aslist=True, fields=['phone', 'status', 'message'])
            except WSException:
                pass

            print res

            for phone, status, status_message in res:
                Message.objects.filter(phone=phone, sending__id=sending_id).update(status=status, 
                                                                                   status_message=status_message)

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
#        messages = dict((str(message.pk) + '-' + str(message.sending_id), message) for message in request)
#        samoussa = SamoussaBackEnd().connect()
#        
#        for entry in samoussa.messages(user_data=messages.iterkeys()):
#            message = messages.get(entry.get('user_data'))
#            message.status = entry.get('status')
#            message.status_message = entry.get('status_message')
#            message.save()
