# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2017  Hybird
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
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.gui.block import QuerysetBlock

from creme.persons import get_contact_model

from creme import sms
from .models import Recipient, Sending, Message


SMSCampaign   = sms.get_smscampaign_model()
MessagingList = sms.get_messaginglist_model()


class _RelatedEntitesBlock(QuerysetBlock):
    def _get_queryset(self, entity):
        raise NotImplementedError

    def detailview_display(self, context):
        entity = context['object']

        return self._render(self.get_block_template_context(
                    context, self._get_queryset(entity),
                    # update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, entity.pk),
                    update_url=reverse('creme_core__reload_detailview_blocks', args=(self.id_, entity.pk)),
        ))


class MessagingListsBlock(_RelatedEntitesBlock):
    id_           = QuerysetBlock.generate_id('sms', 'messaging_lists')
    dependencies  = (MessagingList,)
    verbose_name  = _(u'Messaging lists')
    template_name = 'sms/templatetags/block_messaging_lists.html'
    target_ctypes = (SMSCampaign,)

    def _get_queryset(self, entity):  # NB: entity=campaign
        return entity.lists.all()


class RecipientsBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('sms', 'recipients')
    dependencies  = (Recipient,)
    verbose_name  = _(u'Unlinked recipients')
    template_name = 'sms/templatetags/block_recipients.html'
    target_ctypes = (MessagingList,)

    def detailview_display(self, context):
        pk = context['object'].pk
        return self._render(self.get_block_template_context(
                context,
                Recipient.objects.filter(messaging_list=pk),  # get_recipients() ??? related_name() ?
                # update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, pk),
                update_url=reverse('creme_core__reload_detailview_blocks', args=(self.id_, pk)),
                ct_id=ContentType.objects.get_for_model(Recipient).id,
        ))


class ContactsBlock(_RelatedEntitesBlock):
    id_           = QuerysetBlock.generate_id('sms', 'contacts')
    # dependencies  = (Contact,)
    dependencies  = (get_contact_model(),)
    verbose_name  = _(u'Contacts recipients')
    template_name = 'sms/templatetags/block_contacts.html'
    target_ctypes = (MessagingList,)

    def _get_queryset(self, entity):  # NB: entity=mlist
        return entity.contacts.all()


# TODO: improve credentials (see emails.blocks.MailsBlock) ; must and related entity in Message model
class MessagesBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('sms', 'messages')
    dependencies  = (Message,)
    page_size     = 12
    verbose_name  = _(u'Sent messages')
    template_name = 'sms/templatetags/block_messages.html'

    def detailview_display(self, context):
        sending = context['object']
        return self._render(self.get_block_template_context(
                context, sending.messages.all(),
                # update_url='/sms/campaign/sending/%s/messages/reload/' % sending.pk
                update_url=reverse('sms__reload_messages_block', args=(sending.id,)),
        ))


class SendingsBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('sms', 'sendings')
    dependencies  = (Sending,)
    order_by      = '-date'
    verbose_name  = _(u'Sendings')
    template_name = 'sms/templatetags/block_sendings.html'
    target_ctypes = (SMSCampaign,)

    def detailview_display(self, context):
        campaign = context['object']
        return self._render(self.get_block_template_context(
                    context,
                    Sending.objects.filter(campaign=campaign),  # get_sendings() ??
                    # update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, campaign.pk),
                    update_url=reverse('creme_core__reload_detailview_blocks', args=(self.id_, campaign.pk)),
        ))


messaging_lists_block = MessagingListsBlock()
recipients_block      = RecipientsBlock()
contacts_block        = ContactsBlock()
messages_block        = MessagesBlock()
sendings_block        = SendingsBlock()
