# -*- coding: utf-8 -*-

from creme import documents, persons
from creme.persons.tests.base import (  # NOQA
    skipIfCustomAddress,
    skipIfCustomContact,
    skipIfCustomOrganisation,
)

Document = documents.get_document_model()

Address = persons.get_address_model()
Contact = persons.get_contact_model()
Organisation = persons.get_organisation_model()
