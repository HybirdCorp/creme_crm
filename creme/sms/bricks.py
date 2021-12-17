# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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

from django.utils.translation import gettext_lazy as _

from creme import sms
from creme.creme_core.gui.bricks import QuerysetBrick
from creme.persons import get_contact_model

from .models import Message, Recipient, Sending

SMSCampaign   = sms.get_smscampaign_model()
MessagingList = sms.get_messaginglist_model()


class _RelatedEntitesBrick(QuerysetBrick):
    def _get_queryset(self, entity):
        raise NotImplementedError

    def _update_context(self, context):
        pass

    def detailview_display(self, context):
        btc = self.get_template_context(context, self._get_queryset(context['object']))
        self._update_context(btc)

        return self._render(btc)


class MessagingListsBlock(_RelatedEntitesBrick):
    id_ = QuerysetBrick.generate_id('sms', 'messaging_lists')
    verbose_name = _('Messaging lists')
    dependencies = (MessagingList,)
    template_name = 'sms/bricks/messaging-lists.html'
    target_ctypes = (SMSCampaign,)
    order_by = 'name'

    def _get_queryset(self, entity):  # NB: entity=campaign
        return entity.lists.all()


class RecipientsBrick(QuerysetBrick):
    id_ = QuerysetBrick.generate_id('sms', 'recipients')
    verbose_name = _('Unlinked recipients')
    description = _(
        'Allows to add simple phone number to the current Messaging list. '
        'These numbers are not related to a Contact.\n'
        'Hint: if you want to send SMS to Contacts, you should '
        'use the other block to add recipients.\n'
        'App: SMS'
    )
    dependencies = (Recipient,)
    template_name = 'sms/bricks/recipients.html'
    target_ctypes = (MessagingList,)

    def detailview_display(self, context):
        pk = context['object'].pk
        return self._render(self.get_template_context(
            context,
            Recipient.objects.filter(messaging_list=pk),  # get_recipients() ??? related_name() ?
        ))


class ContactsBrick(_RelatedEntitesBrick):
    id_ = QuerysetBrick.generate_id('sms', 'contacts')
    verbose_name = _('Contacts recipients')
    dependencies = (get_contact_model(),)
    template_name = 'sms/bricks/contacts.html'
    target_ctypes = (MessagingList,)

    def _get_queryset(self, entity):  # NB: entity=mlist
        return entity.contacts.all()

    def _update_context(self, context):
        # TODO: in a templatetag ??
        context['field_hidden'] = context['fields_configs'].get_for_model(
            get_contact_model(),
        ).is_fieldname_hidden('mobile')


class MessagesBrick(QuerysetBrick):
    id_ = QuerysetBrick.generate_id('sms', 'messages')
    verbose_name = _('Sent messages')
    dependencies = (Message,)
    order_by = 'id'
    # page_size = 12
    page_size = QuerysetBrick.page_size * 3
    template_name = 'sms/bricks/messages.html'

    def detailview_display(self, context):
        sending = context['object']
        return self._render(self.get_template_context(context, sending.messages.all()))


class SendingsBrick(QuerysetBrick):
    id_ = QuerysetBrick.generate_id('sms', 'sendings')
    verbose_name = _('Sendings')
    dependencies = (Sending,)
    order_by = '-date'
    template_name = 'sms/bricks/sendings.html'
    target_ctypes = (SMSCampaign,)

    def detailview_display(self, context):
        campaign = context['object']
        return self._render(self.get_template_context(
            context,
            Sending.objects.filter(campaign=campaign),  # get_sendings() ??
        ))
