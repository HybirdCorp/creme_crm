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

from creme_core.gui.block import Block

from emails.models import EmailRecipient, EmailSending, Email


class MailingListsBlock(Block):
    id_           = Block.generate_id('emails', 'mailing_lists')
    verbose_name  = _(u'Listes de diffusion')
    template_name = 'emails/templatetags/block_mailing_lists.html'

    def detailview_display(self, context):
        campaign = context['object']
        return self._render(self.get_block_template_context(context, campaign.mailing_lists.all(),
                                                            update_url='/emails/campaign/%s/mailing_lists/reload/' % campaign.pk))


class EmailRecipientsBlock(Block):
    id_           = Block.generate_id('emails', 'recipients')
    verbose_name  = _(u'Destinataires manuels')
    template_name = 'emails/templatetags/block_recipients.html'

    def detailview_display(self, context):
        pk = context['object'].pk
        return self._render(self.get_block_template_context(context, EmailRecipient.objects.filter(ml__id=pk), #get_recipients() ???
                                                            update_url='/emails/mailing_list/%s/recipients/reload/' % pk))


class ContactsBlock(Block):
    id_           = Block.generate_id('emails', 'contacts')
    verbose_name  = _(u'Contacts destinataires')
    template_name = 'emails/templatetags/block_contacts.html'

    def detailview_display(self, context):
        mailing_list = context['object']
        return self._render(self.get_block_template_context(context, mailing_list.contacts.all(),
                                                            update_url='/emails/mailing_list/%s/contacts/reload/' % mailing_list.pk))


class OrganisationsBlock(Block):
    id_           = Block.generate_id('emails', 'organisations')
    verbose_name  = _(u'Sociétés destinataires')
    template_name = 'emails/templatetags/block_organisations.html'

    def detailview_display(self, context):
        mailing_list = context['object']
        return self._render(self.get_block_template_context(context, mailing_list.organisations.all(),
                                                            update_url='/emails/mailing_list/%s/organisations/reload/' % mailing_list.pk))


class ChildListsBlock(Block):
    id_           = Block.generate_id('emails', 'child_lists')
    verbose_name  = _(u'Listes de diffusion filles')
    template_name = 'emails/templatetags/block_child_lists.html'

    def detailview_display(self, context):
        mailing_list = context['object']
        return self._render(self.get_block_template_context(context, mailing_list.children.all(),
                                                            update_url='/emails/mailing_list/%s/children/reload/' % mailing_list.pk))


class ParentListsBlock(Block):
    id_           = Block.generate_id('emails', 'parent_lists')
    verbose_name  = _(u'Listes de diffusion parentes')
    template_name = 'emails/templatetags/block_parent_lists.html'

    def detailview_display(self, context):
        mailing_list = context['object']
        return self._render(self.get_block_template_context(context, mailing_list.parents_set.all(),
                                                            update_url='/emails/mailing_list/%s/parents/reload/' % mailing_list.pk))


class AttachmentsBlock(Block):
    id_           = Block.generate_id('emails', 'attachments')
    verbose_name  = _(u'Fichiers attachés')
    template_name = 'emails/templatetags/block_attachments.html'

    def detailview_display(self, context):
        template = context['object']
        return self._render(self.get_block_template_context(context, template.attachments.all(),
                                                            update_url='/emails/template/%s/attachments/reload/' % template.pk))


class SendingsBlock(Block):
    id_           = Block.generate_id('emails', 'sendings')
    order_by      = '-sending_date'
    verbose_name  = _(u'Envois')
    template_name = 'emails/templatetags/block_sendings.html'

    def detailview_display(self, context):
        campaign = context['object']
        return self._render(self.get_block_template_context(context, EmailSending.objects.filter(campaign=campaign), #get_sendings() ??
                                                            update_url='/emails/campaign/%s/sendings/reload/' % campaign.pk))


class MailsBlock(Block):
    id_           = Block.generate_id('emails', 'mails')
    page_size     = 12
    verbose_name  = _(u"Mails d'un envoi")
    template_name = 'emails/templatetags/block_mails.html'

    def detailview_display(self, context):
        sending = context['object']
        return self._render(self.get_block_template_context(context, sending.get_mails(),
                                                            update_url='/emails/campaign/sending/%s/mails/reload/' % sending.pk))

    #overload this method because EmailSending is not a CremeEntity (should be ?)
    def detailview_ajax(self, request, entity_id):
        context = {'request': request, 'object': EmailSending.objects.get(id=entity_id)}
        return HttpResponse(JSONEncoder().encode([(self.id_, self.detailview_display(context))]), mimetype="text/javascript")


class MailsHistoryBlock(Block):
    id_           = Block.generate_id('emails', 'mails_history')
    order_by      = '-sending_date'
    verbose_name  = _(u"Historique des mails")
    template_name = 'emails/templatetags/block_mails_history.html'

    def detailview_display(self, context):
        pk = context['object'].pk
        return self._render(self.get_block_template_context(context, Email.objects.filter(recipient_id=pk),
                                                            update_url='/emails/entity/%s/mails_history/reload/' % pk))


mailing_lists_block = MailingListsBlock()
recipients_block    = EmailRecipientsBlock()
contacts_block      = ContactsBlock()
organisations_block = OrganisationsBlock()
child_lists_block   = ChildListsBlock()
parent_lists_block  = ParentListsBlock()
attachments_block   = AttachmentsBlock()
sendings_block      = SendingsBlock()
mails_block         = MailsBlock()
mails_history_block = MailsHistoryBlock()
