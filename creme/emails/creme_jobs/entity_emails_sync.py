################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2022-2025  Hybird
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

import logging
from collections import defaultdict
from email.message import EmailMessage
from os.path import basename, join

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.transaction import atomic
from django.utils.functional import lazy
from django.utils.translation import gettext, ngettext

from creme import persons
from creme.creme_core.auth import EntityCredentials
from creme.creme_core.creme_jobs.base import JobType
from creme.creme_core.models import FileRef, JobResult
from creme.creme_core.models.utils import assign_2_charfield
from creme.creme_core.utils import email
from creme.creme_core.utils.collections import OrderedSet
from creme.creme_core.utils.file_handling import FileCreator
from creme.documents import get_document_model
from creme.emails.models import (
    EmailSyncConfigItem,
    EmailToSync,
    EmailToSyncPerson,
)

logger = logging.getLogger(__name__)
Document = get_document_model()


class _EmailAsKeyDict:
    entity_models = (
        persons.get_contact_model(),
        persons.get_organisation_model(),
    )

    def __init__(self):
        self._users = None
        self._entities = defaultdict(dict)

    def get_user(self, email_address, default=None):
        users = self._users
        if users is None:
            # TODO: what about disabled users?
            users = self._users = {
                user.email: user
                for user in get_user_model().objects.filter(is_staff=False)
            }

        return users.get(email_address, default)

    def get_entity(self, email_address, owner, default=None):
        user = self.get_user(email_address, default=default)
        if user is not None:
            return user.linked_contact

        entities = self._entities[owner.id]
        entity = entities.get(email_address)
        if entity is not None:
            return entity

        for model in self.entity_models:
            model_qs = model.objects.filter(email=email_address)
            filtered_qs = model_qs if owner.is_team else EntityCredentials.filter(
                user=owner,
                perm=EntityCredentials.VIEW | EntityCredentials.LINK,
                queryset=model_qs,
            )
            entity = filtered_qs.first()

            if entity is not None:
                entities[email_address] = entity
                break

        return entity


# TODO: refresh the job when the configuration is edited?
class _EntityEmailsSyncType(JobType):
    id = JobType.generate_id('emails', 'entity_emails_sync')
    verbose_name = lazy(
        lambda: gettext(
            'Synchronize externals emails with {software}'
        ).format(software=settings.SOFTWARE_LABEL),
        str
    )()
    periodic = JobType.PERIODIC

    # TODO: split ?
    def _create_email_to_sync(self, *,
                              config_item: EmailSyncConfigItem,
                              email_id,
                              email_message: EmailMessage,
                              cache: _EmailAsKeyDict,
                              ) -> EmailToSync | None:
        sender_container = email_message['from']
        if sender_container is None:
            logger.info(
                'Email sync: the email "%s" has no FROM & is ignored.', email_id,
            )
            return None

        sender = sender_container.addresses[0].addr_spec

        receivers = OrderedSet()
        for section in ('to', 'cc', 'bcc'):
            receivers_obj = email_message[section]
            if receivers_obj is not None:
                for addr in receivers_obj.addresses:
                    receivers.add(addr.addr_spec)

        if not receivers:
            logger.info(
                'Email sync: the email "%s" has no TO & is ignored.', email_id,
            )
            return None

        # The synchronisation address is not related to a Contact/Organisation,
        # we ignore it.
        receivers.discard(config_item.username)

        owner = (
            cache.get_user(sender)
            or next(
                filter(
                    None,
                    (cache.get_user(receiver) for receiver in receivers)
                ),
                None  # default
            )
            or config_item.default_user
        )
        if owner is None:
            logger.info(
                'Email sync: the email "%s" is related to any & no default user '
                'is configured, so it is ignored.',
                email_id,
            )
            return None

        subject = email_message.get('subject', '')
        body: EmailMessage | None = email_message.get_body(('plain',))
        body_html: EmailMessage | None = email_message.get_body(('html',))
        date_container = email_message['date']

        file_refs = []

        # TODO: better error management ?
        if config_item.keep_attachments:
            rel_media_dir_path = Document._meta.get_field('filedata').upload_to
            untitled_index = 1
            attachment: EmailMessage

            for attachment in email_message.iter_attachments():
                file_name = attachment.get_filename()
                if not file_name:
                    file_name = f'untitled_attachment_{untitled_index}'
                    untitled_index += 1

                abs_path = FileCreator(
                    dir_path=join(settings.MEDIA_ROOT, rel_media_dir_path),
                    name=file_name,
                ).create()

                # NB: we create the FileRef instance as soon as possible to get
                #     the smallest duration when a crash causes a file which
                #     have to be removed by hand (not cleaned by the Cleaner job).
                file_ref = FileRef.objects.create(
                    # user=...,  # ??
                    basename=file_name,
                    filedata=join(rel_media_dir_path, basename(abs_path)),
                    # NB: we create it as temporary in order the file to be clean
                    #     if a crash happens before te FileRef is linked to the
                    #     EmailToSync instance.
                    temporary=True,
                    description=gettext('Attachment for email synchronization'),
                )

                with open(abs_path, 'wb') as f:
                    f.write(attachment.get_content())

                file_refs.append(file_ref)

        with atomic():
            e2s = EmailToSync(
                user=owner,
                body='' if body is None else body.get_content(),
                body_html='' if body_html is None else body_html.get_content(),
                date=None if date_container is None else date_container.datetime,
            )
            assign_2_charfield(e2s, 'subject', subject)
            e2s.save()

            EmailToSyncPerson.objects.create(
                type=EmailToSyncPerson.Type.SENDER,
                email_to_sync=e2s,
                email=sender,
                person=cache.get_entity(sender, owner),
            )

            for i, receiver in enumerate(receivers):
                EmailToSyncPerson.objects.create(
                    type=EmailToSyncPerson.Type.RECIPIENT,
                    email_to_sync=e2s,
                    email=receiver,
                    person=cache.get_entity(receiver, owner),
                    is_main=not i,
                )

            if file_refs:
                # NB: we make the FileRef not temporary to avoid them to be deleted
                #     by the Cleaner Job before the EmailToSync instance is accepted.
                FileRef.objects.filter(
                    id__in=[fref.id for fref in file_refs],
                ).update(temporary=False)
                e2s.attachments.set(file_refs)

        return e2s

    def _execute(self, job):
        cache = _EmailAsKeyDict()

        for config_item in EmailSyncConfigItem.objects.all():
            box_cls = (
                email.POPBox
                if config_item.type == EmailSyncConfigItem.Type.POP else
                email.IMAPBox
            )
            count = valid_count = error_count = ignored_count = 0
            messages = []

            try:
                with box_cls(
                    host=config_item.host,
                    port=config_item.port,
                    use_ssl=config_item.use_ssl,
                    username=config_item.username,
                    password=config_item.password,
                ) as box:
                    for email_id in box:
                        count += 1

                        with box.fetch_email(email_id) as email_message:
                            # NB: these types of error are currently not counted
                            #   - mail deletion
                            #   - client exiting
                            if email_message is None:
                                error_count += 1
                            else:
                                if self._create_email_to_sync(
                                    config_item=config_item,
                                    email_id=email_id,
                                    email_message=email_message,
                                    cache=cache,
                                ) is None:
                                    ignored_count += 1
                                else:
                                    valid_count += 1
            except email.MailBox.Error as e:
                messages.append(str(e))
            else:
                if not count:
                    messages.append(
                        gettext(
                            'There was no message on "{host}" for the user "{user}"'
                        ).format(host=config_item.host, user=config_item.username)
                    )

            if count:
                messages.append(
                    ngettext(
                        'There was {count} valid message on "{host}" for the user "{user}"',
                        'There were {count} valid messages on "{host}" for the user "{user}"',
                        valid_count
                    ).format(count=valid_count, host=config_item.host, user=config_item.username)
                )

            if error_count:
                messages.append(
                    ngettext(
                        'There was {count} erroneous message (see logs for more details)',
                        'There were {count} erroneous messages (see logs for more details)',
                        error_count
                    ).format(count=error_count),
                )

            if ignored_count:
                messages.append(
                    ngettext(
                        'There was {count} ignored message (no known address found)',
                        'There were {count} ignored messages (no known address found)',
                        ignored_count
                    ).format(count=ignored_count),
                )

            JobResult.objects.create(job=job, messages=messages)

    @property
    def results_bricks(self):
        # from creme.creme_core.bricks import JobResultsBrick
        from creme.creme_core.gui.job import JobResultsBrick
        return [JobResultsBrick()]


entity_emails_sync_type = _EntityEmailsSyncType()
