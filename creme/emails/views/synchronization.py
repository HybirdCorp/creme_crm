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
from functools import partial

from django.core.exceptions import PermissionDenied
from django.db.transaction import atomic
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.functional import partition
from django.utils.translation import gettext, ngettext, pgettext_lazy
from django.views.generic.detail import SingleObjectMixin

from creme.creme_core.core.exceptions import BadRequestError, ConflictError
from creme.creme_core.core.workflow import run_workflow_engine
from creme.creme_core.models import Job, Relation
from creme.creme_core.utils import get_from_POST_or_404
from creme.creme_core.utils.serializers import json_encode
from creme.creme_core.views import generic
from creme.documents import get_document_model, get_folder_model
from creme.documents.models import FolderCategory
from creme.emails import get_entityemail_model
from creme.emails.constants import UUID_FOLDER_CAT_EMAILS

from .. import constants
from ..creme_jobs import entity_emails_sync_type
from ..forms import synchronization as sync_forms
from ..models import EmailSyncConfigItem, EmailToSync, EmailToSyncPerson

EntityEmail = get_entityemail_model()


class SynchronizationPortal(generic.BricksView):
    template_name = 'emails/synchronization.html'
    permissions = 'emails'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['job'] = Job.objects.get(type_id=entity_emails_sync_type.id)

        return context


class SynchronizationConfigItemCreation(generic.CremeModelCreationPopup):
    model = EmailSyncConfigItem
    form_class = sync_forms.EmailSyncConfigItemCreationForm
    permissions = 'emails.can_admin'


class SynchronizationConfigItemEdition(generic.CremeModelEditionPopup):
    model = EmailSyncConfigItem
    form_class = sync_forms.EmailSyncConfigItemEditionForm
    pk_url_kwarg = 'item_id'
    title = pgettext_lazy('emails', 'Edit the server configuration')
    submit_label = EmailSyncConfigItem.save_label
    permissions = 'emails.can_admin'


class SynchronizationConfigItemDeletion(generic.CheckedView):
    id_arg = 'id'
    permissions = 'emails.can_admin'

    def post(self, request, **kwargs):
        get_object_or_404(
            EmailSyncConfigItem,
            pk=get_from_POST_or_404(request.POST, self.id_arg),
        ).delete()

        return HttpResponse()


class EmailToSyncPermissionsMixin:
    def check_email_to_sync_permissions(self, instance, user):
        if not user.is_staff:
            owner = instance.user

            if user.id not in owner.teammates if owner.is_team else owner != user:
                raise PermissionDenied(
                    gettext('You cannot edit or delete this email (not yours)')
                )


class EmailToSyncCorrection(generic.CremeModelEditionPopup):
    model = EmailToSync
    form_class = sync_forms.EmailToSyncCorrectionForm
    permissions = 'emails'
    pk_url_kwarg = 'mail_id'

    def check_instance_permissions(self, instance, user):
        types = instance.related_persons.values_list('type', flat=True)
        if len(types) != 1 or types[0] != EmailToSyncPerson.Type.SENDER:
            raise ConflictError(
                'Does not seem to be a forwarded email (only a sender).'
            )


# TODO: factorise with EntitiesDeletion
class _BaseEmailToSyncMultiOperation(EmailToSyncPermissionsMixin, generic.CheckedView):
    ids_arg = 'ids'
    permissions = 'emails'

    def get_ids(self):
        try:
            ids = [
                int(e_id)
                for e_id in get_from_POST_or_404(self.request.POST, self.ids_arg).split(',')
                if e_id
            ]
        except ValueError as e:
            raise BadRequestError(f'Bad POST argument ({e})') from e

        if not ids:
            raise BadRequestError(f'Empty "{self.ids_arg}" argument.')

        return ids

    def perform_operation(self, e2s):
        raise NotImplementedError

    def post(self, request, **kwargs):
        ids = self.get_ids()
        user = request.user
        errors = defaultdict(list)

        # TODO: test workflow
        with atomic(), run_workflow_engine(user=user):
            emails_to_sync = [*EmailToSync.objects.select_for_update().filter(pk__in=ids)]

            len_diff = len(ids) - len(emails_to_sync)
            if len_diff:
                errors[404].append(
                    ngettext(
                        "{count} email doesn't exist or has been removed.",
                        "{count} emails don't exist or have been removed.",
                        len_diff
                    ).format(count=len_diff)
                )

            for e2s in emails_to_sync:
                try:
                    self.check_email_to_sync_permissions(instance=e2s, user=user)
                except PermissionDenied as e:
                    errors[403].append(e.args[0])
                else:
                    try:
                        self.perform_operation(e2s)
                    except ConflictError as e:
                        errors[409].append(e.args[0])

        if not errors:
            status = 200
            message = gettext('Operation successfully completed')
            content_type = None
        else:
            status = min(errors)
            message = json_encode({
                'count': len(ids),
                'errors': [msg for error_messages in errors.values() for msg in error_messages],
            })
            content_type = 'application/json'

        return HttpResponse(message, content_type=content_type, status=status)


class EmailToSyncAcceptation(_BaseEmailToSyncMultiOperation):
    def perform_operation(self, e2s):
        user = e2s.user

        recipients, senders = partition(
            lambda person: person.type == EmailToSyncPerson.Type.SENDER,
            e2s.related_persons.all()
        )

        if len(senders) != 1:
            raise ConflictError('There must be one & only one sender')

        if senders[0].person is None:
            raise ConflictError(
                gettext('The sender is not associated to a Contact/Organisation')
            )

        if len(recipients) == 1:
            main_recipient = recipients[0]
        else:
            main_recipients = [recipient for recipient in recipients if recipient.is_main]
            if len(main_recipients) != 1:
                raise ConflictError(gettext('There is no recipient marked as main'))

            main_recipient = main_recipients[0]

        # TODO: need only one complete recipient + ignore the incomplete ones?
        for recipient in recipients:
            if recipient.person is None:
                raise ConflictError(
                    gettext(
                        'The recipient «{email}» is not associated to a '
                        'Contact/Organisation'
                    ).format(email=recipient.email)
                )

        email = EntityEmail(
            user=user,
            status=EntityEmail.Status.SYNCHRONIZED,
            subject=e2s.subject,
            body=e2s.body,
            body_html=e2s.body_html,
            sender=senders[0].email,
            recipient=main_recipient.email,
            reception_date=e2s.date,
        )
        email.genid_n_save()

        create_relation = partial(Relation.objects.create, user=user, subject_entity=email)
        create_relation(
            type_id=constants.REL_SUB_MAIL_SENT, object_entity=senders[0].person,
        )
        for recipient in recipients:
            create_relation(
                type_id=constants.REL_SUB_MAIL_RECEIVED,
                object_entity=recipient.person,
            )

        attached_files = [*e2s.attachments.all()]
        if attached_files:
            Folder = get_folder_model()
            folder_cat = FolderCategory.objects.get(uuid=UUID_FOLDER_CAT_EMAILS)
            folder = Folder.objects.filter(user=user, category=folder_cat).first()
            if folder is None:
                folder = Folder.objects.create(
                    user=user, category=folder_cat,
                    title=gettext("{username}'s files received by email").format(
                        username=user.username,
                    ),
                )

            create_document = partial(
                get_document_model().objects.create, user=user, linked_folder=folder,
            )

            email.attachments.set([
                create_document(
                    title=file_ref.basename,
                    filedata=file_ref.filedata,
                ) for file_ref in attached_files
            ])

            # We delete the FileRef which are now useless, their files have been "captured".
            e2s.attachments.all().delete()

        e2s.delete()


class EmailToSyncDeletion(_BaseEmailToSyncMultiOperation):
    def perform_operation(self, e2s):
        e2s.attachments.update(temporary=True)
        e2s.delete()


class EmailToSyncPersonEdition(generic.CremeModelEditionPopup):
    model = EmailToSyncPerson
    pk_url_kwarg = 'person_id'
    form_class = sync_forms.EmailToSyncPersonForm
    permissions = 'emails'


class EmailToSyncRecipientMarking(SingleObjectMixin,
                                  EmailToSyncPermissionsMixin,
                                  generic.CheckedView):
    model = EmailToSync
    pk_url_kwarg = 'mail_id'
    permissions = 'emails'
    recipient_id_arg = 'id'

    def post(self, request, **kwargs):
        recipient_id = get_from_POST_or_404(request.POST, self.recipient_id_arg)

        with atomic():
            e2s = self.get_object(self.model.objects.select_for_update())
            self.check_email_to_sync_permissions(instance=e2s, user=request.user)

            if EmailToSyncPerson.objects.filter(
                email_to_sync=e2s,
                type=EmailToSyncPerson.Type.RECIPIENT,
                id=recipient_id,
            ).update(is_main=True) != 1:
                raise Http404(
                    'The instance of EmailToSyncPerson with id=%s cannot be found',
                    recipient_id,
                )

            EmailToSyncPerson.objects.filter(
                email_to_sync=e2s,
                type=EmailToSyncPerson.Type.RECIPIENT,  # Optimisation
            ).exclude(id=recipient_id).update(is_main=False)

        return HttpResponse()


class EmailToSyncRecipientDeletion(SingleObjectMixin,
                                   EmailToSyncPermissionsMixin,
                                   generic.CheckedView):
    model = EmailToSync
    pk_url_kwarg = 'mail_id'
    permissions = 'emails'
    recipient_id_arg = 'id'

    def post(self, request, **kwargs):
        recipient_id = get_from_POST_or_404(request.POST, self.recipient_id_arg)

        with atomic():
            e2s = self.get_object(self.model.objects.select_for_update())
            self.check_email_to_sync_permissions(instance=e2s, user=request.user)

            if e2s.related_persons.count() <= 2:
                raise ConflictError(
                    gettext('You can not delete the last recipient.')
                )

            get_object_or_404(
                EmailToSyncPerson.objects.filter(
                    email_to_sync=e2s,
                    type=EmailToSyncPerson.Type.RECIPIENT,
                ),
                pk=recipient_id,
            ).delete()

        return HttpResponse()


class EmailToSyncAttachmentDeletion(SingleObjectMixin,
                                    EmailToSyncPermissionsMixin,
                                    generic.CheckedView):
    model = EmailToSync
    pk_url_kwarg = 'mail_id'
    permissions = 'emails'
    fileref_id_arg = 'id'

    @atomic
    def post(self, request, **kwargs):
        fileref_id = get_from_POST_or_404(request.POST, self.fileref_id_arg)

        with atomic():
            e2s = self.get_object(self.model.objects.select_for_update())
            self.check_email_to_sync_permissions(instance=e2s, user=request.user)

            e2s.attachments.filter(id=fileref_id).update(temporary=True)
            e2s.attachments.remove(fileref_id)

        return HttpResponse()
