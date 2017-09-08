import warnings

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.gui.bricks import QuerysetBrick
from creme.creme_core.models import Relation

from . import get_entityemail_model, constants
from .bricks import (
    _HTMLBodyBrick as _HTMLBodyBlock,
    EmailHTMLBodyBrick as EmailHTMLBodyBlock,
    TemplateHTMLBodyBrick as TemplateHTMLBodyBlock,
    _RelatedEntitesBrick as _RelatedEntitesBlock,
    MailingListsBrick as MailingListsBlock,
    EmailRecipientsBrick as EmailRecipientsBlock,
    ContactsBrick as ContactsBlock,
    OrganisationsBrick as OrganisationsBlock,
    ChildListsBrick as ChildListsBlock,
    ParentListsBrick as ParentListsBlock,
    AttachmentsBrick as AttachmentsBlock,
    SendingsBrick as SendingsBlock,
    MailsBrick as MailsBlock,
    LwMailsHistoryBrick as LwMailsHistoryBlock,
    SignaturesBrick as SignaturesBlock,
)

warnings.warn('emails.blocks is deprecated ; use emails.bricks instead.', DeprecationWarning)

EntityEmail = get_entityemail_model()


class MailsHistoryBlock(QuerysetBrick):
    id_           = QuerysetBrick.generate_id('emails', 'mails_history')
    dependencies  = (EntityEmail, Relation)
    order_by      = '-sending_date'
    verbose_name  = _(u"Emails history")
    template_name = 'emails/templatetags/block_mails_history.html'
    relation_type_deps = (constants.REL_OBJ_MAIL_SENDED,
                          constants.REL_OBJ_MAIL_RECEIVED,
                          constants.REL_OBJ_RELATED_TO,
                         )

    _RTYPE_IDS = [constants.REL_SUB_MAIL_SENDED,
                  constants.REL_SUB_MAIL_RECEIVED,
                  constants.REL_SUB_RELATED_TO,
                 ]
    _STATUSES = [constants.MAIL_STATUS_SYNCHRONIZED,
                 constants.MAIL_STATUS_SYNCHRONIZED_SPAM,
                 constants.MAIL_STATUS_SYNCHRONIZED_WAITING,
                ]

    def detailview_display(self, context):
        entity = context['object']
        pk = entity.pk
        entityemail_pk = Relation.objects.filter(type__pk__in=self._RTYPE_IDS, object_entity=pk) \
                                         .values_list('subject_entity', flat=True) \
                                         .distinct()

        # return self._render(self.get_block_template_context(
        return self._render(self.get_template_context(
                    context,
                    EntityEmail.objects.filter(is_deleted=False, pk__in=entityemail_pk),
                    # update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, pk),
                    update_url=reverse('creme_core__reload_detailview_blocks', args=(self.id_, pk)),
                    sent_status=constants.MAIL_STATUS_SENT,
                    sync_statuses=self._STATUSES,
                    rtypes=','.join(self.relation_type_deps),
                    creation_perm=context['user'].has_perm_to_create(EntityEmail),
        ))


email_html_body_block    = EmailHTMLBodyBlock()
template_html_body_block = TemplateHTMLBodyBlock()
mailing_lists_block      = MailingListsBlock()
email_recipients_block   = EmailRecipientsBlock()
contacts_block           = ContactsBlock()
organisations_block      = OrganisationsBlock()
child_lists_block        = ChildListsBlock()
parent_lists_block       = ParentListsBlock()
attachments_block        = AttachmentsBlock()
sendings_block           = SendingsBlock()
mails_block              = MailsBlock()
mails_history_block      = MailsHistoryBlock()
signatures_block         = SignaturesBlock()

blocks_list = (
    email_html_body_block,
    template_html_body_block,
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
    signatures_block,
)


if apps.is_installed('creme.crudity'):
    from creme.crudity.blocks import CrudityQuerysetBlock


    class _SynchronizationMailsBlock(CrudityQuerysetBlock):
        dependencies = (EntityEmail,)
        order_by = '-reception_date'
        configurable = False


    class WaitingSynchronizationMailsBlock(_SynchronizationMailsBlock):
        id_ = _SynchronizationMailsBlock.generate_id('emails', 'waiting_synchronisation')
        verbose_name = u'Incoming Emails to sync'
        template_name = 'emails/templatetags/block_synchronization.html'

        def detailview_display(self, context):
            super(WaitingSynchronizationMailsBlock, self).detailview_display(context)
            context['entityemail_ct_id'] = ContentType.objects.get_for_model(EntityEmail).id
            context['rtypes'] = (constants.REL_SUB_MAIL_SENDED,
                                 constants.REL_SUB_MAIL_RECEIVED,
                                 constants.REL_SUB_RELATED_TO,
                                )

            waiting_mails = EntityEmail.objects.filter(status=constants.MAIL_STATUS_SYNCHRONIZED_WAITING)
            if self.is_sandbox_by_user:
                waiting_mails = waiting_mails.filter(user=context['user'])

            return self._render(self.get_template_context(
                    context, waiting_mails,
                    # update_url='/emails/sync_blocks/reload',
                    update_url=reverse('emails__crudity_reload_sync_blocks'),
            ))


    class SpamSynchronizationMailsBlock(_SynchronizationMailsBlock):
        id_ = _SynchronizationMailsBlock.generate_id('emails', 'synchronised_as_spam')
        verbose_name = u'Spam emails'
        template_name = 'emails/templatetags/block_synchronization_spam.html'

        def detailview_display(self, context):
            super(SpamSynchronizationMailsBlock, self).detailview_display(context)
            context['entityemail_ct_id'] = ContentType.objects.get_for_model(EntityEmail).id

            waiting_mails = EntityEmail.objects.filter(status=constants.MAIL_STATUS_SYNCHRONIZED_SPAM)
            if self.is_sandbox_by_user:
                waiting_mails = waiting_mails.filter(user=context['user'])

            return self._render(self.get_template_context(
                        context, waiting_mails,
                        # update_url='/emails/sync_blocks/reload',
                        update_url=reverse('emails__crudity_reload_sync_blocks'),
            ))

    mail_waiting_sync_block = WaitingSynchronizationMailsBlock()
    mail_spam_sync_block = SpamSynchronizationMailsBlock()

    blocks_list += (
        mail_waiting_sync_block,
        mail_spam_sync_block,
    )
