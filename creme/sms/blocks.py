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

from django.http import HttpResponse
from django.utils.simplejson import JSONEncoder
from django.utils.translation import ugettext_lazy as _

from creme_core.gui.block import QuerysetBlock

from sms.models import Recipient, Sending, Message


class SendListsBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('sms', 'sendlists')
    verbose_name  = _(u'Listes de diffusion')
    template_name = 'sms/templatetags/block_sendlists.html'

    def detailview_display(self, context):
        campaign = context['object']
        return self._render(self.get_block_template_context(context, campaign.sendlists.all(),
                                                            update_url='/sms/campaign/%s/sendlist/reload/' % campaign.pk))


class RecipientsBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('sms', 'recipients')
    verbose_name  = _(u'Destinataires manuels')
    template_name = 'sms/templatetags/block_recipients.html'

    def detailview_display(self, context):
        pk = context['object'].pk
        return self._render(self.get_block_template_context(context, Recipient.objects.filter(sendlist__id=pk), #get_recipients() ???
                                                            update_url='/sms/sendlist/%s/recipients/reload/' % pk))


class ContactsBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('sms', 'contacts')
    verbose_name  = _(u'Contacts destinataires')
    template_name = 'sms/templatetags/block_contacts.html'

    def detailview_display(self, context):
        sendlist = context['object']
        return self._render(self.get_block_template_context(context, sendlist.contacts.all(),
                                                            update_url='/sms/sendlist/%s/contacts/reload/' % sendlist.pk))


class MessagesBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('sms', 'messages')
    verbose_name  = _(u'Messages envoyés')
    template_name = 'sms/templatetags/block_messages.html'

    def detailview_display(self, context):
        sending = context['object']
        return self._render(self.get_block_template_context(context, sending.messages.all(),
                                                            update_url='/sms/campaign/sending/%s/messages/reload/' % sending.pk))

    def detailview_ajax(self, request, entity_id):
        context = {'request': request, 'object': Sending.objects.get(id=entity_id)}
        return HttpResponse(JSONEncoder().encode([(self.id_, self.detailview_display(context))]), mimetype="text/javascript")

#
#class OrganisationsBlock(Block):
#    id_           = Block.generate_id('emails', 'organisations')
#    verbose_name  = _(u'Sociétés destinataires')
#    template_name = 'emails/templatetags/block_organisations.html'
#
#    def detailview_display(self, context):
#        sendlist = context['object']
#        return self._render(self.get_block_template_context(context, sendlist.organisations.all(),
#                                                            update_url='/sms/sendlist/%s/organisations/reload/' % sendlist.pk))
#

class SendingsBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('sms', 'sendings')
    order_by      = '-date'
    verbose_name  = _(u'Envois')
    template_name = 'sms/templatetags/block_sendings.html'

    def detailview_display(self, context):
        campaign = context['object']
        return self._render(self.get_block_template_context(context, Sending.objects.filter(campaign=campaign), #get_sendings() ??
                                                            update_url='/sms/campaign/%s/sendings/reload/' % campaign.pk))

#
#class MailsBlock(Block):
#    id_           = Block.generate_id('emails', 'mails')
#    page_size     = 12
#    verbose_name  = _(u"Mails d'un envoi")
#    template_name = 'emails/templatetags/block_mails.html'
#
#    def detailview_display(self, context):
#        sending = context['object']
#        return self._render(self.get_block_template_context(context, sending.get_mails(),
#                                                            update_url='/emails/campaign/sending/%s/mails/reload/' % sending.pk))
#
#    #overload this method because EmailSending is not a CremeEntity (should be ?)
#    def detailview_ajax(self, request, entity_id):
#        context = {'request': request, 'object': EmailSending.objects.get(id=entity_id)}
#        return HttpResponse(JSONEncoder().encode([(self.id_, self.detailview_display(context))]), mimetype="text/javascript")

#class MailsHistoryBlock(Block):
#    id_           = Block.generate_id('emails', 'mails_history')
#    order_by      = '-sending_date'
#    verbose_name  = _(u"Historique des mails")
#    template_name = 'emails/templatetags/block_mails_history.html'
#
#    def detailview_display(self, context):
#        pk = context['object'].pk
#        return self._render(self.get_block_template_context(context, Email.objects.filter(recipient_id=pk),
#                                                            update_url='/emails/entity/%s/mails_history/reload/' % pk))


sendlists_block     = SendListsBlock()
recipients_block    = RecipientsBlock()
contacts_block      = ContactsBlock()
messages_block      = MessagesBlock()
sendings_block      = SendingsBlock()

#organisations_block = OrganisationsBlock()

#mails_block         = MailsBlock()
#mails_history_block = MailsHistoryBlock()
