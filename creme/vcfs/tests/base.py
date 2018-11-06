# -*- coding: utf-8 -*-

try:
    from creme import documents, persons

    from creme.persons.tests.base import (skipIfCustomAddress, skipIfCustomContact,
            skipIfCustomOrganisation)

    Document = documents.get_document_model()

    Address = persons.get_address_model()
    Contact = persons.get_contact_model()
    Organisation = persons.get_organisation_model()
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))
