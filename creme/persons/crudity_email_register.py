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
from crudity.backends.email import CreateFromEmailBackend
from crudity.backends.email.create.infopath import InfopathCreateFromEmail

from persons.models.contact import Contact

create_contact_settings    = settings.PERSONS_CONTACT_FROM_EMAIL.get(CREATE)
CREATE_CONTACT_PASSWORD    = create_contact_settings.get("password")
CREATE_CONTACT_LIMIT_FROMS = create_contact_settings.get("limit_froms")
CREATE_CONTACT_IN_SANDBOX  = create_contact_settings.get("in_sandbox", True)
CREATE_CONTACT_BODY_MAP    = create_contact_settings.get("body_map", {})
CREATE_CONTACT_SUBJECT     = create_contact_settings.get("subject")

create_contact_infopath_settings    = settings.PERSONS_CONTACT_FROM_EMAIL_INFOPATH.get(CREATE)
CREATE_CONTACT_INFOPATH_PASSWORD    = create_contact_infopath_settings.get("password")
CREATE_CONTACT_INFOPATH_LIMIT_FROMS = create_contact_infopath_settings.get("limit_froms")
CREATE_CONTACT_INFOPATH_IN_SANDBOX  = create_contact_infopath_settings.get("in_sandbox", True)
CREATE_CONTACT_INFOPATH_BODY_MAP    = create_contact_infopath_settings.get("body_map", {})
CREATE_CONTACT_INFOPATH_SUBJECT     = create_contact_infopath_settings.get("subject")


class CreateContactFromEmail(CreateFromEmailBackend):
    password       = CREATE_CONTACT_PASSWORD
    limit_froms    = CREATE_CONTACT_LIMIT_FROMS
    in_sandbox     = CREATE_CONTACT_IN_SANDBOX
    body_map       = CREATE_CONTACT_BODY_MAP
    model          = Contact
    subject        = CREATE_CONTACT_SUBJECT


class CreateContactFromEmailInfopath(InfopathCreateFromEmail):
    password       = CREATE_CONTACT_INFOPATH_PASSWORD
    limit_froms    = CREATE_CONTACT_INFOPATH_LIMIT_FROMS
    in_sandbox     = CREATE_CONTACT_INFOPATH_IN_SANDBOX
    body_map       = CREATE_CONTACT_INFOPATH_BODY_MAP
    model          = Contact
    subject        = CREATE_CONTACT_INFOPATH_SUBJECT


crud_register = {
    CREATE: [
        (CreateContactFromEmail.subject,         CreateContactFromEmail()),
        (CreateContactFromEmailInfopath.subject, CreateContactFromEmailInfopath()),
    ],
}
