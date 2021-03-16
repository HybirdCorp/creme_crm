# -*- coding: utf-8 -*-

from creme.creme_core.gui.menu import CreationEntry, ListviewEntry
from creme.creme_core.models import FakeContact, FakeOrganisation


class FakeContactCreationEntry(CreationEntry):
    id = 'creme_core-create_contact'
    model = FakeContact


class FakeContactsEntry(ListviewEntry):
    id = 'creme_core-list_contact'
    model = FakeContact


class FakeOrganisationCreationEntry(CreationEntry):
    id = 'creme_core-create_organisation'
    model = FakeOrganisation


class FakeOrganisationsEntry(ListviewEntry):
    id = 'creme_core-list_organisation'
    model = FakeOrganisation
