################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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

from collections import defaultdict

from django.urls import reverse
from django.utils.functional import partition
from django.utils.translation import gettext_lazy as _

from creme import documents, emails, persons
from creme.creme_core.gui.bricks import QuerysetBrick, SimpleBrick
from creme.creme_core.models import Relation, RelationType

from . import constants
from .models import (
    EmailRecipient,
    EmailSending,
    EmailSendingConfigItem,
    EmailSignature,
    EmailSyncConfigItem,
    EmailToSync,
    EmailToSyncPerson,
    LightWeightEmail,
)
from .utils import SignatureRenderer

Document = documents.get_document_model()

Contact      = persons.get_contact_model()
Organisation = persons.get_organisation_model()

EmailTemplate = emails.get_emailtemplate_model()
EmailCampaign = emails.get_emailcampaign_model()
EntityEmail   = emails.get_entityemail_model()
MailingList   = emails.get_mailinglist_model()


class EntityEmailBarHatBrick(SimpleBrick):
    # NB: we do not set an ID because it's the main Header Brick.
    template_name = 'emails/bricks/mail-hat-bar.html'


class _HTMLBodyBrick(SimpleBrick):
    verbose_name = _('HTML body')
    template_name = 'emails/bricks/html-body.html'

    def _get_body_url(self, instance):
        return reverse(
            'creme_core__sanitized_html_field', args=(instance.id, 'body_html'),
        )

    def get_template_context(self, context, **extra_kwargs):
        return super().get_template_context(
            context,
            body_url=self._get_body_url(context['object']),
            **extra_kwargs
        )


class EmailHTMLBodyBrick(_HTMLBodyBrick):
    id = _HTMLBodyBrick.generate_id('emails', 'email_html_body')
    dependencies = (EntityEmail,)
    target_ctypes = (EntityEmail,)
    permissions = 'emails'


class TemplateHTMLBodyBrick(_HTMLBodyBrick):
    id = _HTMLBodyBrick.generate_id('emails', 'template_html_body')
    dependencies = (EmailTemplate,)
    target_ctypes = (EmailTemplate,)
    permissions = 'emails'


class SendingHTMLBodyBrick(_HTMLBodyBrick):
    id = _HTMLBodyBrick.generate_id('emails', 'sending_html_body')
    dependencies = (EmailSending,)
    permissions = 'emails'
    configurable = False
    # TODO: remove when the bricks is no more globally registered
    target_ctypes = (EmailSending,)  # Security purpose

    def _get_body_url(self, instance):
        return reverse('emails__sending_body', args=(instance.id,))


class _RelatedEntitiesBrick(QuerysetBrick):
    # id            = 'SET ME'
    # dependencies  = 'SET ME'
    # verbose_name  = 'SET ME'
    # template_name = 'SET ME'
    permissions = 'emails'

    def _get_queryset(self, entity):  # OVERRIDE ME
        raise NotImplementedError

    def _update_context(self, context):
        pass

    def detailview_display(self, context):
        btc = self.get_template_context(context, self._get_queryset(context['object']))
        self._update_context(btc)

        return self._render(btc)


class MailingListsBrick(_RelatedEntitiesBrick):
    id = QuerysetBrick.generate_id('emails', 'mailing_lists')
    verbose_name = _('Mailing lists')
    description = _(
        'Allows to add Mailing lists to the current campaign. '
        'A campaign needs to be linked a least to one Mailing list in '
        'order to send emails.\n'
        'Note: do not worry, if an email address is contained by several lists, '
        'only one email will be sent to this address.\n'
        'App: Emails'
    )
    dependencies = (MailingList,)
    template_name = 'emails/bricks/mailing-lists.html'
    target_ctypes = (EmailCampaign,)
    order_by = 'name'

    def _get_queryset(self, entity):  # NB: entity==campaign
        return entity.mailing_lists.all()


class EmailRecipientsBrick(QuerysetBrick):
    id = QuerysetBrick.generate_id('emails', 'recipients')
    verbose_name = _('Not linked recipients')
    description = _(
        'Allows to add simple email addresses to the current Mailing list. '
        'These addresses are not related to a Contact or an Organisation.\n'
        'Hint: if you want to send emails to Contacts/Organisations, you should '
        'use the other blocks to add recipients.\n'
        'App: Emails'
    )
    dependencies = (EmailRecipient,)
    template_name = 'emails/bricks/recipients.html'
    target_ctypes = (MailingList,)
    permissions = 'emails'

    def detailview_display(self, context):
        mailing_list = context['object']
        return self._render(self.get_template_context(
            context,
            EmailRecipient.objects.filter(ml=mailing_list.id),  # get_recipients() ???
        ))


class ContactsBrick(_RelatedEntitiesBrick):
    id = _RelatedEntitiesBrick.generate_id('emails', 'contacts')
    verbose_name = _('Contact-recipients')
    dependencies = (Contact,)
    template_name = 'emails/bricks/contacts.html'
    target_ctypes = (MailingList,)

    def _get_queryset(self, entity):  # NB: entity==mailing_list
        return entity.contacts.select_related('civility')


class OrganisationsBrick(_RelatedEntitiesBrick):
    id = _RelatedEntitiesBrick.generate_id('emails', 'organisations')
    verbose_name = _('Organisations recipients')
    dependencies = (Organisation,)
    template_name = 'emails/bricks/organisations.html'
    target_ctypes = (MailingList,)

    def _get_queryset(self, entity):  # NB: entity==mailing_list
        return entity.organisations.all()


class ChildListsBrick(_RelatedEntitiesBrick):
    id = _RelatedEntitiesBrick.generate_id('emails', 'child_lists')
    verbose_name = _('Child mailing lists')
    dependencies = (MailingList,)
    template_name = 'emails/bricks/child-lists.html'
    target_ctypes = (MailingList,)
    permissions = 'emails'
    order_by = 'name'

    def _get_queryset(self, entity):  # NB: entity==mailing_list
        return entity.children.all()


class ParentListsBrick(_RelatedEntitiesBrick):
    id = _RelatedEntitiesBrick.generate_id('emails', 'parent_lists')
    verbose_name = _('Parent mailing lists')
    dependencies = (MailingList,)
    template_name = 'emails/bricks/parent-lists.html'
    target_ctypes = (MailingList,)
    permissions = 'emails'
    order_by = 'name'

    def _get_queryset(self, entity):  # NB: entity==mailing_list
        return entity.parents_set.all()


class AttachmentsBrick(_RelatedEntitiesBrick):
    id = _RelatedEntitiesBrick.generate_id('emails', 'attachments')
    verbose_name = _('Attachments')
    dependencies = (Document,)
    template_name = 'emails/bricks/attachments.html'
    target_ctypes = (EmailTemplate,)
    permissions = 'emails'
    order_by = 'title'

    def _get_queryset(self, entity):  # NB: entity==mailtemplate
        return entity.attachments.all()


class SendingConfigItemsBrick(QuerysetBrick):
    id = QuerysetBrick.generate_id('emails', 'sending_config_items')
    dependencies = (EmailSendingConfigItem,)
    order_by = 'id'
    template_name = 'emails/bricks/sending-config-items.html'
    configurable = False
    # permissions = 'emails.can_admin' => auto by creme_config views

    def detailview_display(self, context):
        return self._render(self.get_template_context(
            context, EmailSendingConfigItem.objects.all(),
        ))


class SendingsBrick(QuerysetBrick):
    id = QuerysetBrick.generate_id('emails', 'sendings')
    verbose_name = _('Emails sending')
    description = _(
        'Allows to send emails to all the recipients listed in the related Mailing lists.\n'
        'App: Emails'
    )
    dependencies = (EmailSending,)
    order_by = '-sending_date'
    template_name = 'emails/bricks/sendings.html'
    target_ctypes = (EmailCampaign,)
    permissions = 'emails'

    def detailview_display(self, context):
        campaign = context['object']
        return self._render(self.get_template_context(
            context,
            # TODO: use related_name i.e:campaign.sendings_set.all()
            EmailSending.objects.filter(campaign=campaign.id),
            config_available=EmailSendingConfigItem.objects.exists(),
        ))


class SendingBrick(SimpleBrick):
    id = SimpleBrick.generate_id('emails', 'sending')
    verbose_name = _('Information')
    dependencies = (EmailSending,)
    permissions = 'emails'
    template_name = 'emails/bricks/sending.html'
    configurable = False
    # TODO: remove when the bricks is no more globally registered
    target_ctypes = (EmailSending,)  # Security purpose


class MailsBrick(QuerysetBrick):
    id = QuerysetBrick.generate_id('emails', 'mails')
    verbose_name = 'Emails of a sending'
    dependencies = (LightWeightEmail,)
    permissions = 'emails'
    order_by = 'id'
    page_size = QuerysetBrick.page_size * 3
    template_name = 'emails/bricks/lw-mails.html'
    configurable = False
    # TODO: remove when the bricks is no more globally registered
    target_ctypes = (EmailSending,)  # Security purpose

    def detailview_display(self, context):
        return self._render(self.get_template_context(
            context,
            context['object'].mails_set.prefetch_related('real_recipient'),
        ))


class MailsHistoryBrick(QuerysetBrick):
    id = QuerysetBrick.generate_id('emails', 'mails_history')
    verbose_name = _('Emails history')
    description = _(
        'Displays the Emails linked to the current entity with a relationship '
        '«sent the email», «received the email» or «related to the email». '
        'Allows you to send emails too.\n'
        'App: Emails'
    )
    dependencies = (EntityEmail, Relation)
    order_by = '-sending_date'
    template_name = 'emails/bricks/mails-history.html'
    relation_type_deps = (
        constants.REL_OBJ_MAIL_SENT,
        constants.REL_OBJ_MAIL_RECEIVED,
        constants.REL_OBJ_RELATED_TO,
    )
    # Important because it can be displayed on entities' detail-views of other apps
    permissions = 'emails'

    def detailview_display(self, context):
        pk = context['object'].pk
        entityemail_ids = Relation.objects.filter(
            type__symmetric_type_id__in=self.relation_type_deps,
            object_entity=pk,
        ).values_list('subject_entity', flat=True).distinct()

        relation_types = RelationType.objects.filter(id__in=self.relation_type_deps)

        return self._render(self.get_template_context(
            context,
            EntityEmail.objects.filter(is_deleted=False, pk__in=entityemail_ids),
            relation_types=relation_types,
            relation_types_all_disabled=not any(
                rtype.enabled for rtype in relation_types
            ),
        ))


class MailPopupBrick(SimpleBrick):
    id = QuerysetBrick.generate_id('emails', 'mail_popup')
    verbose_name = 'Detail popup of email'
    dependencies = (EntityEmail,)
    permissions = 'emails'
    template_name = 'emails/bricks/mail-popup.html'
    configurable = False
    target_ctypes = (EntityEmail,)  # Security purpose only


class LwMailPopupBrick(SimpleBrick):
    id = QuerysetBrick.generate_id('emails', 'lw_mail_popup')
    verbose_name = 'Detail popup of LightWeight email'
    dependencies = (LightWeightEmail,)
    permissions = 'emails'
    template_name = 'emails/bricks/lw-mail-popup.html'
    configurable = False
    target_ctypes = (LightWeightEmail,)  # Security purpose only


class LwMailsHistoryBrick(QuerysetBrick):
    id = QuerysetBrick.generate_id('emails', 'lw_mails_history')
    verbose_name = _('Campaigns emails history')
    description = _(
        'Displays the emails (sent from Campaigns) received by the current entity.\n'
        'App: Emails'
    )
    dependencies = (LightWeightEmail,)
    permissions = 'emails'
    template_name = 'emails/bricks/lw-mails-history.html'
    order_by = '-sending_date'

    def detailview_display(self, context):
        pk = context['object'].pk
        return self._render(self.get_template_context(
            context,
            LightWeightEmail.objects.filter(
                recipient_entity=pk,
            ).select_related('sending').prefetch_related('sending__campaign'),
        ))


class MySignaturesBrick(QuerysetBrick):
    id = QuerysetBrick.generate_id('emails', 'my_signatures')
    verbose_name = _('My signatures')
    dependencies = (EmailSignature,)
    order_by = 'name'
    template_name = 'emails/bricks/signatures.html'
    configurable = False
    permissions = 'emails'

    signature_render_cls = SignatureRenderer

    def detailview_display(self, context):
        btc = self.get_template_context(
            context,
            EmailSignature.objects.filter(user=context['user']).prefetch_related('images')
        )

        for signature in btc['page'].object_list:
            signature.renderer = self.signature_render_cls(
                signature=signature, domain='test.org',
            )

        return self._render(btc)


class EmailSyncConfigItemsBrick(QuerysetBrick):
    id = QuerysetBrick.generate_id('emails', 'sync_config_items')
    dependencies = (EmailSyncConfigItem,)
    order_by = 'id'
    template_name = 'emails/bricks/sync-config-items.html'
    configurable = False
    # permissions = 'emails.can_admin' => auto by creme_config views

    def detailview_display(self, context):
        return self._render(self.get_template_context(
            context, EmailSyncConfigItem.objects.all(),
        ))


class EmailsToSyncBrick(QuerysetBrick):
    id = QuerysetBrick.generate_id('emails', 'emails_to_sync')
    dependencies = (EmailToSync,)
    order_by = 'id'
    template_name = 'emails/bricks/emails-to-sync.html'
    configurable = False
    permissions = 'emails'
    page_size = 50

    def detailview_display(self, context):
        user = context['user']

        qs = EmailToSync.objects.prefetch_related('attachments')
        if not user.is_staff:
            qs = qs.filter(user__in=[user, *user.teams])

        btc = self.get_template_context(context, qs)
        related_persons = defaultdict(list)

        for r_person in EmailToSyncPerson.objects.order_by('-is_main', 'id').filter(
            # TODO: <email_to_sync__in=btc['page'].object_list> when MySQL supports it...
            email_to_sync__in=[*btc['page'].object_list],
        ).prefetch_related('person'):
            related_persons[r_person.email_to_sync_id].append(r_person)

        for e2s in btc['page'].object_list:
            email_persons = related_persons[e2s.id]

            e2s.recipients, e2s.senders = partition(
                (lambda rp: rp.type == EmailToSyncPerson.Type.SENDER),
                email_persons
            )
            # TODO: do not accept if no sender/recipient ? (should not happen...)
            e2s.can_be_accepted = not any(
                related.person is None for related in email_persons
            )

        return self._render(btc)
