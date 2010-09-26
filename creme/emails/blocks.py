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

from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponse
from django.template.context import RequestContext
from django.utils.simplejson import JSONEncoder
from django.utils.translation import ugettext_lazy as _

from creme_core.gui.block import QuerysetBlock
from creme_core.utils import jsonify

from persons.models import Contact, Organisation

from documents.models import Document

from emails.models import EmailRecipient, EmailSending, LightWeightEmail, MailingList, EntityEmail
from emails.models.mail import MAIL_STATUS_SYNCHRONIZED_SPAM, MAIL_STATUS_SYNCHRONIZED_WAITING, MAIL_STATUS


__all__ = ['mailing_lists_block', 'recipients_block', 'contacts_block', 'organisations_block',
           'child_lists_block', 'parent_lists_block', 'attachments_block', 'sendings_block',
           'mails_block', 'mails_history_block', 'mail_waiting_sync_block', 'mail_spam_sync_block']

class MailingListsBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('emails', 'mailing_lists')
    dependencies  = (MailingList,)
    verbose_name  = _(u'Mailing lists')
    template_name = 'emails/templatetags/block_mailing_lists.html'

    def detailview_display(self, context):
        campaign = context['object']
        return self._render(self.get_block_template_context(context, campaign.mailing_lists.all(),
                                                            update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, campaign.pk),
                                                            ))


class EmailRecipientsBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('emails', 'recipients')
    dependencies  = (EmailRecipient,)
    verbose_name  = _(u'Unlinked recipients')
    template_name = 'emails/templatetags/block_recipients.html'

    def detailview_display(self, context):
        mailing_list = context['object']
        return self._render(self.get_block_template_context(context, EmailRecipient.objects.filter(ml=mailing_list), #get_recipients() ???
                                                            update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, mailing_list.pk),
                                                            ))


class ContactsBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('emails', 'contacts')
    dependencies  = (Contact,)
    verbose_name  = _(u'Contacts recipients')
    template_name = 'emails/templatetags/block_contacts.html'

    def detailview_display(self, context):
        mailing_list = context['object']
        return self._render(self.get_block_template_context(context, mailing_list.contacts.all(),
                                                            update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, mailing_list.pk),
                                                            ))


class OrganisationsBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('emails', 'organisations')
    dependencies  = (Organisation,)
    verbose_name  = _(u'Organisations recipients')
    template_name = 'emails/templatetags/block_organisations.html'

    def detailview_display(self, context):
        mailing_list = context['object']
        return self._render(self.get_block_template_context(context, mailing_list.organisations.all(),
                                                            update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, mailing_list.pk),
                                                            ))


class ChildListsBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('emails', 'child_lists')
    dependencies  = (MailingList,)
    verbose_name  = _(u'Child mailing lists')
    template_name = 'emails/templatetags/block_child_lists.html'

    def detailview_display(self, context):
        mailing_list = context['object']
        return self._render(self.get_block_template_context(context, mailing_list.children.all(),
                                                            update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, mailing_list.pk),
                                                            ))


class ParentListsBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('emails', 'parent_lists')
    dependencies  = (MailingList,)
    verbose_name  = _(u'Parent mailing lists')
    template_name = 'emails/templatetags/block_parent_lists.html'

    def detailview_display(self, context):
        mailing_list = context['object']
        return self._render(self.get_block_template_context(context, mailing_list.parents_set.all(),
                                                            update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, mailing_list.pk),
                                                            ))


class AttachmentsBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('emails', 'attachments')
    dependencies  = (Document,)
    verbose_name  = _(u'Attachments')
    template_name = 'emails/templatetags/block_attachments.html'

    def detailview_display(self, context):
        template = context['object']
        return self._render(self.get_block_template_context(context, template.attachments.all(),
                                                            update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, template.pk),
                                                            ))


class SendingsBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('emails', 'sendings')
    dependencies  = (EmailSending,)
    order_by      = '-sending_date'
    verbose_name  = _(u'Sendings')
    template_name = 'emails/templatetags/block_sendings.html'

    def detailview_display(self, context):
        campaign = context['object']
        return self._render(self.get_block_template_context(context, EmailSending.objects.filter(campaign=campaign), #get_sendings() ??
                                                            update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, campaign.pk),
                                                            ))


class MailsBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('emails', 'mails')
    dependencies  = (LightWeightEmail,)
    page_size     = 12
    verbose_name  = _(u"Emails of a sending")
    template_name = 'emails/templatetags/block_mails.html'

    def detailview_display(self, context):
        sending = context['object']
        return self._render(self.get_block_template_context(context, sending.get_mails(),
                                                            update_url='/emails/campaign/sending/%s/mails/reload/' % sending.pk
                                                            ))

    #Useful method because EmailSending is not a CremeEntity (should be ?) --> generic view in creme_core (problems with credemtials ?) ??
    #TODO: use RequestContext
    @jsonify
    def detailview_ajax(self, request, entity_id):
        from creme_core.gui.block import BlocksManager
        context = {
                'request':              request,
                'object':               EmailSending.objects.get(id=entity_id),
                BlocksManager.var_name: BlocksManager(),
            }

        return [(self.id_, self.detailview_display(context))]


class MailsHistoryBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('emails', 'mails_history')
    dependencies  = (LightWeightEmail,)
    order_by      = '-sending_date'
    verbose_name  = _(u"Emails history")
    template_name = 'emails/templatetags/block_mails_history.html'
    configurable  = True

    def detailview_display(self, context):
        pk = context['object'].pk
        return self._render(self.get_block_template_context(context, LightWeightEmail.objects.filter(recipient_id=pk),
                                                            update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, pk), #TODO: test me!!!
                                                            ))


class _SynchronizationMailsBlock(QuerysetBlock):
    dependencies  = (EntityEmail,)
    order_by      = '-reception_date'

    def __init__(self, *args, **kwargs):
        super(_SynchronizationMailsBlock, self).__init__()

    @jsonify
    def detailview_ajax(self, request):
        context = RequestContext(request)
        context.update({
            'MAIL_STATUS': MAIL_STATUS,
            'entityemail_ct_id': ContentType.objects.get_for_model(EntityEmail).id,
        })

        return [(self.id_, self.detailview_display(context))]


class WaitingSynchronizationMailsBlock(_SynchronizationMailsBlock):
    id_           = QuerysetBlock.generate_id('emails', 'waiting_synchronisation')
    verbose_name  = _(u'Incoming Emails to sync')
    template_name = 'emails/templatetags/block_synchronization.html'

    def detailview_display(self, context):
        context.update({'MAIL_STATUS': MAIL_STATUS})
        return self._render(self.get_block_template_context(context, EntityEmail.objects.filter(status=MAIL_STATUS_SYNCHRONIZED_WAITING),
#                                                            update_url='/creme_core/blocks/reload/basic/%s/' % self.id_
                                                            update_url='/emails/sync_blocks/reload'
                                                            ))


class SpamSynchronizationMailsBlock(_SynchronizationMailsBlock):
    id_           = QuerysetBlock.generate_id('emails', 'synchronised_as_spam')
    verbose_name  = _(u'Spam emails')
    template_name = 'emails/templatetags/block_synchronization_spam.html'

    def detailview_display(self, context):
        context.update({'MAIL_STATUS': MAIL_STATUS})
        return self._render(self.get_block_template_context(context, EntityEmail.objects.filter(status=MAIL_STATUS_SYNCHRONIZED_SPAM),
#                                                            update_url='/creme_core/blocks/reload/basic/%s/' % self.id_
                                                            update_url='/emails/sync_blocks/reload'
                                                            ))


mailing_lists_block     = MailingListsBlock()
recipients_block        = EmailRecipientsBlock()
contacts_block          = ContactsBlock()
organisations_block     = OrganisationsBlock()
child_lists_block       = ChildListsBlock()
parent_lists_block      = ParentListsBlock()
attachments_block       = AttachmentsBlock()
sendings_block          = SendingsBlock()
mails_block             = MailsBlock()
mails_history_block     = MailsHistoryBlock()
mail_waiting_sync_block = WaitingSynchronizationMailsBlock()
mail_spam_sync_block    = SpamSynchronizationMailsBlock()
