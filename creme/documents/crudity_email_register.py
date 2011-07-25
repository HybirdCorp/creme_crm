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

from django.conf import settings

from crudity import CREATE
from crudity.backends.email.create.infopath import InfopathCreateFromEmail

from documents.models.document import Document

create_document_infopath_settings    = settings.DOCUMENTS_DOCUMENT_FROM_EMAIL_INFOPATH.get(CREATE)
CREATE_DOCUMENT_INFOPATH_PASSWORD    = create_document_infopath_settings.get("password")
CREATE_DOCUMENT_INFOPATH_LIMIT_FROMS = create_document_infopath_settings.get("limit_froms")
CREATE_DOCUMENT_INFOPATH_IN_SANDBOX  = create_document_infopath_settings.get("in_sandbox", True)
CREATE_DOCUMENT_INFOPATH_BODY_MAP    = create_document_infopath_settings.get("body_map", {})
CREATE_DOCUMENT_INFOPATH_SUBJECT     = create_document_infopath_settings.get("subject")


class CreateDocumentFromEmailInfopath(InfopathCreateFromEmail):
    password       = CREATE_DOCUMENT_INFOPATH_PASSWORD
    limit_froms    = CREATE_DOCUMENT_INFOPATH_LIMIT_FROMS
    in_sandbox     = CREATE_DOCUMENT_INFOPATH_IN_SANDBOX
    body_map       = CREATE_DOCUMENT_INFOPATH_BODY_MAP
    model          = Document
    subject        = CREATE_DOCUMENT_INFOPATH_SUBJECT


crud_register = {
    CREATE: [
        (CreateDocumentFromEmailInfopath.subject, CreateDocumentFromEmailInfopath()),
    ],
}
