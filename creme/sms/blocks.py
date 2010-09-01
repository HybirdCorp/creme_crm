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
from creme_core.utils import jsonify

from persons.models import Contact

from sms.models import Recipient, Sending, Message, MessagingList


class MessagingListsBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('sms', 'messaging_lists')
    dependencies  = (MessagingList,)
    verbose_name  = _(u'Messaging lists')
    template_name = 'sms/templatetags/block_messaging_lists.html'

    def detailview_display(self, context):
        campaign = context['object']
        return self._render(self.get_block_template_context(context, campaign.lists.all(),
                                                            update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, campaign.pk),
                                                            ))


class RecipientsBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('sms', 'recipients')
    dependencies  = (Recipient,)
    verbose_name  = _(u'Unlinked recipients')
    template_name = 'sms/templatetags/block_recipients.html'

    def detailview_display(self, context):
        pk = context['object'].pk
        return self._render(self.get_block_template_context(context, Recipient.objects.filter(messaging_list=pk), #get_recipients() ??? related_name()
                                                            update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, pk),
                                                            ))


class ContactsBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('sms', 'contacts')
    dependencies  = (Contact,)
    verbose_name  = _(u'Contacts recipients')
    template_name = 'sms/templatetags/block_contacts.html'

    def detailview_display(self, context):
        mlist = context['object']
        return self._render(self.get_block_template_context(context, mlist.contacts.all(),
                                                            update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, mlist.pk),
                                                            ))


class MessagesBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('sms', 'messages')
    dependencies  = (Message,)
    page_size     = 12
    verbose_name  = _(u'Sent messages')
    template_name = 'sms/templatetags/block_messages.html'

    def detailview_display(self, context):
        sending = context['object']
        return self._render(self.get_block_template_context(context, sending.messages.all(),
                                                            update_url='/sms/campaign/sending/%s/messages/reload/' % sending.pk
                                                            ))

    #Useful method because EmailSending is not a CremeEntity (should be ?) --> generic view in creme_core (problems with credemtials ?) ??
    @jsonify
    def detailview_ajax(self, request, entity_id):
        from creme_core.gui.block import BlocksManager
        context = {
                'request':              request,
                'object':               Sending.objects.get(id=entity_id),
                BlocksManager.var_name: BlocksManager(),
            }

        return [(self.id_, self.detailview_display(context))]


class SendingsBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('sms', 'sendings')
    dependencies  = (Sending,)
    order_by      = '-date'
    verbose_name  = _(u'Sendings')
    template_name = 'sms/templatetags/block_sendings.html'

    def detailview_display(self, context):
        campaign = context['object']
        return self._render(self.get_block_template_context(context, Sending.objects.filter(campaign=campaign), #get_sendings() ??
                                                            update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, campaign.pk),
                                                            ))


messaging_lists_block = MessagingListsBlock()
recipients_block      = RecipientsBlock()
contacts_block        = ContactsBlock()
messages_block        = MessagesBlock()
sendings_block        = SendingsBlock()
