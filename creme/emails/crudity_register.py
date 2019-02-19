# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2019  Hybird
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

from functools import partial
from itertools import chain
from os.path import basename

from django.db.transaction import atomic
from django.utils.translation import ugettext as _

from creme.creme_core.models import Relation
from creme.creme_core.views.file_handling import handle_uploaded_file

from creme import documents
from creme.documents.constants import REL_OBJ_RELATED_2_DOC, DOCUMENTS_FROM_EMAILS
from creme.documents.models import FolderCategory

from creme.crudity.backends.models import CrudityBackend
from creme.crudity.inputs.base import CrudityInput
from creme.crudity.inputs.email import CreateEmailInput
from creme.crudity.models import History

from . import get_entityemail_model, bricks
from .constants import MAIL_STATUS_SYNCHRONIZED_WAITING


Folder   = documents.get_folder_model()
Document = documents.get_document_model()

EntityEmail = get_entityemail_model()


class EntityEmailBackend(CrudityBackend):
    model           = EntityEmail
    brick_classes   = (bricks.WaitingSynchronizationMailsBrick, bricks.SpamSynchronizationMailsBrick)
    attachment_path = ['upload', 'emails', 'attachments']

    @atomic
    def fetcher_fallback(self, email, current_user, *args, **kwargs):
        if not CrudityInput().authorize_senders(self, email.senders):
            return

        if self.is_sandbox_by_user:
            current_user = CreateEmailInput.get_owner(True, sender=email.senders[0])

        current_user_id = current_user.id

        # TODO: only if at least one attachment
        folder = Folder.objects.get_or_create(title=_("{username}'s files received by email").format(
                                                            username=current_user.username,
                                                        ),
                                              category=FolderCategory.objects.get(pk=DOCUMENTS_FROM_EMAILS),
                                              parent_folder=None,
                                              defaults={'user': current_user},
                                             )[0]

        mail = EntityEmail(status=MAIL_STATUS_SYNCHRONIZED_WAITING,
                           # body=email.body.encode('utf-8'),
                           body=email.body,
                           # body_html=email.body_html.encode('utf-8'),
                           body_html=email.body_html,
                           sender=', '.join(set(email.senders)),
                           recipient=', '.join(set(chain(email.tos, email.ccs))),
                           subject=email.subject,
                           user_id=current_user_id,
                          )
        if email.dates:
            mail.reception_date = email.dates[0]
        mail.genid_n_save()

        attachment_path = self.attachment_path
        # TODO: only if at least one attachment
        create_relation = partial(Relation.objects.create, type_id=REL_OBJ_RELATED_2_DOC,
                                  object_entity=mail, user_id=current_user_id,
                                 )
        create_doc = partial(Document.objects.create,
                             user_id=current_user_id, folder=folder,
                             description=_('Received with the mail {}').format(mail),
                            )

        for attachment in email.attachments:
            filename, file_ = attachment
            path = handle_uploaded_file(file_, path=attachment_path, name=filename)
            doc = create_doc(title='{} (mail {})'.format(basename(path), mail.id),
                             filedata=path,
                            )

            create_relation(subject_entity=doc)

        History.objects.create(entity=mail,
                               action='create',
                               source='email - raw',
                               description=_('Creation of {entity}').format(entity=mail),
                               user=current_user,
                              )


backends = [EntityEmailBackend]
