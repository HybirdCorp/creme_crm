# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2012  Hybird
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

from django.core.exceptions import PermissionDenied
from django.template.context import RequestContext #
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType

from creme_core.models import Relation #, CremeEntity
from creme_core.gui.block import SimpleBlock, QuerysetBlock, list4url
from creme_core.utils import jsonify #

from persons.models import Contact, Organisation

from documents.models import Document

from emails.constants import *
from emails.models import *

from crudity.blocks import CrudityQuerysetBlock


class EntityEmailBlock(SimpleBlock):
    template_name = 'emails/templatetags/block_mail.html'


class _RelatedEntitesBlock(QuerysetBlock):
    #id_           = 'SET ME'
    #dependencies  = 'SET ME'
    #verbose_name  = 'SET ME'
    #template_name = 'SET ME'

    def _get_queryset(self, entity): #OVERLOAD ME
        raise NotImplementedError

    def detailview_display(self, context):
        entity = context['object']
        btc = self.get_block_template_context(context, self._get_queryset(entity),
                                              update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, entity.pk),
                                             )

        #CremeEntity.populate_credentials(btc['page'].object_list, context['user'])

        return self._render(btc)


class MailingListsBlock(_RelatedEntitesBlock):
    id_           = QuerysetBlock.generate_id('emails', 'mailing_lists')
    dependencies  = (MailingList,)
    verbose_name  = _(u'Mailing lists')
    template_name = 'emails/templatetags/block_mailing_lists.html'
    target_ctypes = (EmailCampaign,)

    def _get_queryset(self, entity): #entity=campaign
        return entity.mailing_lists.all()


class EmailRecipientsBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('emails', 'recipients')
    dependencies  = (EmailRecipient,)
    verbose_name  = _(u'Unlinked recipients')
    template_name = 'emails/templatetags/block_recipients.html'
    target_ctypes = (MailingList,)

    def detailview_display(self, context):
        mailing_list = context['object']
        return self._render(self.get_block_template_context(context, EmailRecipient.objects.filter(ml=mailing_list.id), #get_recipients() ???
                                                            update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, mailing_list.pk),
                                                            ct_id=ContentType.objects.get_for_model(EmailRecipient).id,
                                                           ))


class ContactsBlock(_RelatedEntitesBlock):
    id_           = QuerysetBlock.generate_id('emails', 'contacts')
    dependencies  = (Contact,)
    verbose_name  = _(u'Contacts recipients')
    template_name = 'emails/templatetags/block_contacts.html'
    target_ctypes = (MailingList,)

    def _get_queryset(self, entity): #entity=mailing_list
        return entity.contacts.select_related('civility')


class OrganisationsBlock(_RelatedEntitesBlock):
    id_           = QuerysetBlock.generate_id('emails', 'organisations')
    dependencies  = (Organisation,)
    verbose_name  = _(u'Organisations recipients')
    template_name = 'emails/templatetags/block_organisations.html'
    target_ctypes = (MailingList,)

    def _get_queryset(self, entity): #entity=mailing_list
        return entity.organisations.all()


class ChildListsBlock(_RelatedEntitesBlock):
    id_           = QuerysetBlock.generate_id('emails', 'child_lists')
    dependencies  = (MailingList,)
    verbose_name  = _(u'Child mailing lists')
    template_name = 'emails/templatetags/block_child_lists.html'
    target_ctypes = (MailingList,)

    def _get_queryset(self, entity): #entity=mailing_list
        return entity.children.all()


class ParentListsBlock(_RelatedEntitesBlock):
    id_           = QuerysetBlock.generate_id('emails', 'parent_lists')
    dependencies  = (MailingList,)
    verbose_name  = _(u'Parent mailing lists')
    template_name = 'emails/templatetags/block_parent_lists.html'
    target_ctypes = (MailingList,)

    def _get_queryset(self, entity): #entity=mailing_list
        return entity.parents_set.all()


class AttachmentsBlock(_RelatedEntitesBlock):
    id_           = QuerysetBlock.generate_id('emails', 'attachments')
    dependencies  = (Document,)
    verbose_name  = _(u'Attachments')
    template_name = 'emails/templatetags/block_attachments.html'
    target_ctypes = (EmailTemplate,)

    def _get_queryset(self, entity): #entity=mailtemplate
        return entity.attachments.all()


class SendingsBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('emails', 'sendings')
    dependencies  = (EmailSending,)
    order_by      = '-sending_date'
    verbose_name  = _(u'Sendings')
    template_name = 'emails/templatetags/block_sendings.html'
    target_ctypes = (EmailCampaign,)

    def detailview_display(self, context):
        campaign = context['object']
        return self._render(self.get_block_template_context(context, EmailSending.objects.filter(campaign=campaign.id), #TODO: use related_name i.e:campaign.sendings_set.all()
                                                            update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, campaign.pk),
                                                            ct_id=ContentType.objects.get_for_model(EmailSending).id,
                                                           ))


class MailsBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('emails', 'mails')
    dependencies  = (LightWeightEmail,)
    page_size     = 12
    verbose_name  = u"Emails of a sending"
    template_name = 'emails/templatetags/block_mails.html'
    configurable  = False

    def detailview_display(self, context):
        sending = context['object']
        btc = self.get_block_template_context(context, sending.get_mails().select_related('recipient_entity'),
                                              update_url='/emails/campaign/sending/%s/mails/reload/' % sending.pk,
                                              ct_id=ContentType.objects.get_for_model(LightWeightEmail).id,
                                             )

        #CremeEntity.populate_credentials([mail.recipient_entity for mail in btc['page'].object_list if mail.recipient_entity],
                                         #context['user']
                                        #)

        return self._render(btc)


class MailsHistoryBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('emails', 'mails_history')
    dependencies  = (EntityEmail, Relation)
    order_by      = '-sending_date'
    verbose_name  = _(u"Emails history")
    template_name = 'emails/templatetags/block_mails_history.html'
    relation_type_deps = (REL_OBJ_MAIL_SENDED, REL_OBJ_MAIL_RECEIVED, REL_OBJ_RELATED_TO)

    def detailview_display(self, context):
        entity = context['object']
        pk = entity.pk
        entityemail_pk = Relation.objects.filter(type__pk__in=[REL_SUB_MAIL_SENDED, REL_SUB_MAIL_RECEIVED, REL_SUB_RELATED_TO], object_entity=pk) \
                                         .values_list('subject_entity', flat=True) \
                                         .distinct()

        return self._render(self.get_block_template_context(context,
                                                            EntityEmail.objects.filter(pk__in=entityemail_pk),
                                                            update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, pk),
                                                            sent_status=MAIL_STATUS_SENT,
                                                            sync_statuses=[MAIL_STATUS_SYNCHRONIZED, MAIL_STATUS_SYNCHRONIZED_SPAM, MAIL_STATUS_SYNCHRONIZED_WAITING],
                                                            rtypes=','.join(self.relation_type_deps),
                                                            creation_perm=context['user'].has_perm_to_create(EntityEmail),
                                                           ))

class LwMailsHistoryBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('emails', 'lw_mails_history')
    dependencies  = (LightWeightEmail,)
    order_by      = '-sending_date'
    verbose_name  = _(u"Campaigns emails history")
    template_name = 'emails/templatetags/block_lw_mails_history.html'

    def detailview_display(self, context):
        pk = context['object'].pk
        return self._render(self.get_block_template_context(context,
                                                            LightWeightEmail.objects.filter(recipient_entity=pk).select_related('sending'),
                                                            update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, pk),
                                                           ))


class _SynchronizationMailsBlock(CrudityQuerysetBlock):
    dependencies  = (EntityEmail,)
    order_by      = '-reception_date'
    configurable  = False

    @jsonify
    def detailview_ajax(self, request):
        context = RequestContext(request)
        return [(self.id_, self.detailview_display(context))]


class WaitingSynchronizationMailsBlock(_SynchronizationMailsBlock):
    id_           = QuerysetBlock.generate_id('emails', 'waiting_synchronisation')
    verbose_name  = u'Incoming Emails to sync'
    template_name = 'emails/templatetags/block_synchronization.html'

    def detailview_display(self, context):
        super(WaitingSynchronizationMailsBlock, self).detailview_display(context)
        context['MAIL_STATUS'] = MAIL_STATUS
        context['entityemail_ct_id'] = ContentType.objects.get_for_model(EntityEmail).id
        context['rtypes'] = ','.join([REL_SUB_MAIL_SENDED, REL_SUB_MAIL_RECEIVED, REL_SUB_RELATED_TO])

        waiting_mails = EntityEmail.objects.filter(status=MAIL_STATUS_SYNCHRONIZED_WAITING)
        if self.is_sandbox_by_user:
            waiting_mails = waiting_mails.filter(user=context['user'])

        return self._render(self.get_block_template_context(context, waiting_mails,
                                                            update_url='/emails/sync_blocks/reload'
                                                           ))


#TODO: factorise with WaitingSynchronizationMailsBlock ??
class SpamSynchronizationMailsBlock(_SynchronizationMailsBlock):
    id_           = QuerysetBlock.generate_id('emails', 'synchronised_as_spam')
    verbose_name  = u'Spam emails'
    template_name = 'emails/templatetags/block_synchronization_spam.html'

    def detailview_display(self, context):
        super(SpamSynchronizationMailsBlock, self).detailview_display(context)
        context['MAIL_STATUS'] = MAIL_STATUS
        context['entityemail_ct_id'] = ContentType.objects.get_for_model(EntityEmail).id

        waiting_mails = EntityEmail.objects.filter(status=MAIL_STATUS_SYNCHRONIZED_SPAM)
        if self.is_sandbox_by_user:
            waiting_mails = waiting_mails.filter(user=context['user'])

        return self._render(self.get_block_template_context(context, waiting_mails,
                                                            update_url='/emails/sync_blocks/reload'
                                                           ))


class SignaturesBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('emails', 'signatures')
    dependencies  = (EmailSignature,)
    order_by      = 'name'
    verbose_name  = _(u'Email signatures')
    template_name = 'emails/templatetags/block_signatures.html'
    target_apps   = ('emails',)

    def portal_display(self, context, ct_ids):
        if not context['user'].has_perm('emails'):
            raise PermissionDenied('Error: you are not allowed to view this block: %s' % self.id_)

        return self._render(self.get_block_template_context(context, EmailSignature.objects.filter(user=context['user']),
                                                            update_url='/creme_core/blocks/reload/portal/%s/%s/' % (self.id_, list4url(ct_ids)),
                                                           ))


mailing_lists_block     = MailingListsBlock()
email_recipients_block  = EmailRecipientsBlock()
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
signatures_block        = SignaturesBlock()

blocks_list = (
        mailing_lists_block,
        email_recipients_block,
        contacts_block,
        organisations_block,
        child_lists_block,
        parent_lists_block,
        attachments_block,
        sendings_block,
        mails_block,
        mails_history_block,
        LwMailsHistoryBlock(),
        mail_waiting_sync_block,
        mail_spam_sync_block,
        signatures_block,
    )
