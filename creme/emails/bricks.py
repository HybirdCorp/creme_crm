# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2020  Hybird
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

from django.apps import apps
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from creme import documents, emails, persons
from creme.creme_core.gui.bricks import Brick, QuerysetBrick, SimpleBrick
from creme.creme_core.models import CremeEntity, Relation

from . import constants
from .models import (
    EmailRecipient,
    EmailSending,
    EmailSignature,
    LightWeightEmail,
)

Document      = documents.get_document_model()
Contact       = persons.get_contact_model()
Organisation  = persons.get_organisation_model()
EmailTemplate = emails.get_emailtemplate_model()
EmailCampaign = emails.get_emailcampaign_model()
EntityEmail   = emails.get_entityemail_model()
MailingList   = emails.get_mailinglist_model()


class EntityEmailBarHatBrick(SimpleBrick):
    # NB: we do not set an ID because it's the main Header Brick.
    template_name = 'emails/bricks/mail-hat-bar.html'


class _HTMLBodyBrick(Brick):
    verbose_name  = _('HTML body')
    template_name = 'emails/bricks/html-body.html'

    def _get_body_url(self, instance):
        return reverse('creme_core__sanitized_html_field',
                       args=(instance.id, 'body_html')
                      )

    def detailview_display(self, context):
        return self._render(self.get_template_context(
            context,
            body_url=self._get_body_url(context['object']),
        ))


class EmailHTMLBodyBrick(_HTMLBodyBrick):
    id_           = QuerysetBrick.generate_id('emails', 'email_html_body')
    dependencies  = (EntityEmail,)
    target_ctypes = (EntityEmail,)


class TemplateHTMLBodyBrick(_HTMLBodyBrick):
    id_           = QuerysetBrick.generate_id('emails', 'template_html_body')
    dependencies  = (EmailTemplate,)
    target_ctypes = (EmailTemplate,)


class SendingHTMLBodyBrick(_HTMLBodyBrick):
    id_           = QuerysetBrick.generate_id('emails', 'sending_html_body')
    dependencies  = (EmailSending,)
    configurable = False

    def _get_body_url(self, instance):
        return reverse('emails__sending_body', args=(instance.id,))


class _RelatedEntitesBrick(QuerysetBrick):
    # id_           = 'SET ME'
    # dependencies  = 'SET ME'
    # verbose_name  = 'SET ME'
    # template_name = 'SET ME'

    def _get_queryset(self, entity):  # OVERLOAD ME
        raise NotImplementedError

    def _update_context(self, context):
        pass

    def detailview_display(self, context):
        btc = self.get_template_context(context, self._get_queryset(context['object']))
        self._update_context(btc)

        return self._render(btc)


class MailingListsBrick(_RelatedEntitesBrick):
    id_           = QuerysetBrick.generate_id('emails', 'mailing_lists')
    dependencies  = (MailingList,)
    verbose_name  = _('Mailing lists')
    template_name = 'emails/bricks/mailing-lists.html'
    target_ctypes = (EmailCampaign,)
    order_by      = 'name'

    def _get_queryset(self, entity):  # entity=campaign
        return entity.mailing_lists.all()


class EmailRecipientsBrick(QuerysetBrick):
    id_           = QuerysetBrick.generate_id('emails', 'recipients')
    dependencies  = (EmailRecipient,)
    verbose_name  = _('Unlinked recipients')
    template_name = 'emails/bricks/recipients.html'
    target_ctypes = (MailingList,)

    def detailview_display(self, context):
        mailing_list = context['object']
        return self._render(self.get_template_context(
            context,
            EmailRecipient.objects.filter(ml=mailing_list.id),  # get_recipients() ???
        ))


class ContactsBrick(_RelatedEntitesBrick):
    id_           = QuerysetBrick.generate_id('emails', 'contacts')
    dependencies  = (Contact,)
    verbose_name  = _('Contacts recipients')
    template_name = 'emails/bricks/contacts.html'
    target_ctypes = (MailingList,)

    def _get_queryset(self, entity):  # entity=mailing_list
        return entity.contacts.select_related('civility')

    def _update_context(self, context):
        # TODO: in a templatetag ??
        context['field_hidden'] = context['fields_configs'].get_4_model(Contact) \
                                                           .is_fieldname_hidden('email')


class OrganisationsBrick(_RelatedEntitesBrick):
    id_           = QuerysetBrick.generate_id('emails', 'organisations')
    dependencies  = (Organisation,)
    verbose_name  = _('Organisations recipients')
    template_name = 'emails/bricks/organisations.html'
    target_ctypes = (MailingList,)

    def _get_queryset(self, entity):  # entity=mailing_list
        return entity.organisations.all()

    def _update_context(self, context):
        context['field_hidden'] = context['fields_configs'].get_4_model(Organisation) \
                                                           .is_fieldname_hidden('email')


class ChildListsBrick(_RelatedEntitesBrick):
    id_           = QuerysetBrick.generate_id('emails', 'child_lists')
    dependencies  = (MailingList,)
    verbose_name  = _('Child mailing lists')
    template_name = 'emails/bricks/child-lists.html'
    target_ctypes = (MailingList,)
    order_by      = 'name'

    def _get_queryset(self, entity):  # entity=mailing_list
        return entity.children.all()


class ParentListsBrick(_RelatedEntitesBrick):
    id_           = QuerysetBrick.generate_id('emails', 'parent_lists')
    dependencies  = (MailingList,)
    verbose_name  = _('Parent mailing lists')
    template_name = 'emails/bricks/parent-lists.html'
    target_ctypes = (MailingList,)
    order_by      = 'name'

    def _get_queryset(self, entity):  # entity=mailing_list
        return entity.parents_set.all()


class AttachmentsBrick(_RelatedEntitesBrick):
    id_           = QuerysetBrick.generate_id('emails', 'attachments')
    dependencies  = (Document,)
    verbose_name  = _('Attachments')
    template_name = 'emails/bricks/attachments.html'
    target_ctypes = (EmailTemplate,)
    order_by      = 'title'

    def _get_queryset(self, entity):  # entity=mailtemplate
        return entity.attachments.all()


class SendingsBrick(QuerysetBrick):
    id_           = QuerysetBrick.generate_id('emails', 'sendings')
    dependencies  = (EmailSending,)
    order_by      = '-sending_date'
    verbose_name  = _('Sendings')
    template_name = 'emails/bricks/sendings.html'
    target_ctypes = (EmailCampaign,)

    def detailview_display(self, context):
        campaign = context['object']
        return self._render(self.get_template_context(
            context,
            EmailSending.objects.filter(campaign=campaign.id),  # TODO: use related_name i.e:campaign.sendings_set.all()
        ))


class SendingBrick(SimpleBrick):
    id_           = SimpleBrick.generate_id('emails', 'sending')
    dependencies  = (EmailSending,)
    verbose_name  = 'Info on the sending'
    template_name = 'emails/bricks/sending.html'
    configurable  = False


class MailsBrick(QuerysetBrick):
    id_           = QuerysetBrick.generate_id('emails', 'mails')
    dependencies  = (LightWeightEmail,)
    order_by      = 'id'
    # page_size     = 12
    page_size     = QuerysetBrick.page_size * 3
    verbose_name  = 'Emails of a sending'
    template_name = 'emails/bricks/lw-mails.html'
    configurable  = False

    def detailview_display(self, context):
        btc = self.get_template_context(
            context,
            # context['object'].get_mails().select_related('recipient_entity'),
            context['object'].mails_set.select_related('recipient_entity'),
        )

        CremeEntity.populate_real_entities(
            [*filter(None, (lw_mail.recipient_entity for lw_mail in btc['page'].object_list))]
        )

        return self._render(btc)


class MailsHistoryBrick(QuerysetBrick):
    id_           = QuerysetBrick.generate_id('emails', 'mails_history')
    dependencies  = (EntityEmail, Relation)
    order_by      = '-sending_date'
    verbose_name  = _('Emails history')
    template_name = 'emails/bricks/mails-history.html'
    relation_type_deps = (
        constants.REL_OBJ_MAIL_SENDED,
        constants.REL_OBJ_MAIL_RECEIVED,
        constants.REL_OBJ_RELATED_TO,
    )

    _RTYPE_IDS = [
        constants.REL_SUB_MAIL_SENDED,
        constants.REL_SUB_MAIL_RECEIVED,
        constants.REL_SUB_RELATED_TO,
    ]

    def detailview_display(self, context):
        pk = context['object'].pk
        entityemail_ids = Relation.objects.filter(type__pk__in=self._RTYPE_IDS,
                                                  object_entity=pk,
                                                 ) \
                                          .values_list('subject_entity', flat=True) \
                                          .distinct()

        return self._render(self.get_template_context(
            context,
            EntityEmail.objects.filter(is_deleted=False, pk__in=entityemail_ids),
            rtype_ids=self.relation_type_deps,
            creation_perm=context['user'].has_perm_to_create(EntityEmail),
        ))


class MailPopupBrick(SimpleBrick):
    id_           = QuerysetBrick.generate_id('emails', 'mail_popup')
    dependencies  = (EntityEmail,)
    verbose_name  = 'Detail popup of Email'
    template_name = 'emails/bricks/mail-popup.html'
    configurable  = False


class LwMailPopupBrick(SimpleBrick):
    id_           = QuerysetBrick.generate_id('emails', 'lw_mail_popup')
    dependencies  = (LightWeightEmail,)
    verbose_name  = 'Detail popup of LightWeight Email'
    template_name = 'emails/bricks/lw-mail-popup.html'
    configurable  = False


class LwMailsHistoryBrick(QuerysetBrick):
    id_           = QuerysetBrick.generate_id('emails', 'lw_mails_history')
    dependencies  = (LightWeightEmail,)
    order_by      = '-sending_date'
    verbose_name  = _('Campaigns emails history')
    template_name = 'emails/bricks/lw-mails-history.html'

    def detailview_display(self, context):
        pk = context['object'].pk
        return self._render(self.get_template_context(
            context,
            LightWeightEmail.objects
                            .filter(recipient_entity=pk)
                            .select_related('sending'),
        ))


class MySignaturesBrick(QuerysetBrick):
    id_           = QuerysetBrick.generate_id('emails', 'my_signatures')
    dependencies  = (EmailSignature,)
    order_by      = 'name'
    verbose_name  = 'My Email signatures'
    template_name = 'emails/bricks/signatures.html'
    configurable  = False
    # NB: used by the view creme_core.views.bricks.reload_basic ; None means "No special permission required".
    #     The brick must be visible by all users ; we check permissions in the render to disabled only forbidden things.
    permission    = None

    def detailview_display(self, context):
        user = context['user']

        return self._render(self.get_template_context(
            context,
            EmailSignature.objects.filter(user=user),
            has_app_perm=user.has_perm('emails'),
       ))


if apps.is_installed('creme.crudity'):
    # from creme.crudity.bricks import CrudityQuerysetBrick
    from creme.crudity.bricks import BaseWaitingActionsBrick
    from creme.crudity.utils import is_sandbox_by_user

    # class _SynchronizationMailsBrick(CrudityQuerysetBrick):
    class _SynchronizationMailsBrick(BaseWaitingActionsBrick):
        dependencies = (EntityEmail,)
        order_by     = '-reception_date'
        configurable = False

        # def __init__(self, backend):
        #     super().__init__()
        #     self.backend = backend


    class WaitingSynchronizationMailsBrick(_SynchronizationMailsBrick):
        id_           = _SynchronizationMailsBrick.generate_id('emails', 'waiting_synchronisation')
        verbose_name  = 'Incoming Emails to sync'
        template_name = 'emails/bricks/synchronization.html'

        def detailview_display(self, context):
            super().detailview_display(context)
            context['rtypes'] = (constants.REL_SUB_MAIL_SENDED,
                                 constants.REL_SUB_MAIL_RECEIVED,
                                 constants.REL_SUB_RELATED_TO,
                                )

            waiting_mails = EntityEmail.objects.filter(
                is_deleted=False,
                status=constants.MAIL_STATUS_SYNCHRONIZED_WAITING,
            )

            # if self.is_sandbox_by_user:
            if is_sandbox_by_user():
                waiting_mails = waiting_mails.filter(user=context['user'])

            return self._render(self.get_template_context(
                context, waiting_mails,
                backend=self.backend,
            ))

    # TODO: factorise with WaitingSynchronizationMailsBrick ??
    # TODO: credentials ?? (see template too)
    class SpamSynchronizationMailsBrick(_SynchronizationMailsBrick):
        id_           = _SynchronizationMailsBrick.generate_id('emails', 'synchronised_as_spam')
        verbose_name  = 'Spam emails'
        template_name = 'emails/bricks/synchronization-spam.html'

        def detailview_display(self, context):
            super().detailview_display(context)

            waiting_mails = EntityEmail.objects.filter(
                is_deleted=False,
                status=constants.MAIL_STATUS_SYNCHRONIZED_SPAM,
            )
            # if self.is_sandbox_by_user:
            if is_sandbox_by_user():
                waiting_mails = waiting_mails.filter(user=context['user'])

            return self._render(self.get_template_context(
                context, waiting_mails,
                backend=self.backend,
            ))
