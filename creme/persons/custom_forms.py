# -*- coding: utf-8 -*-

from django.utils.translation import gettext_lazy as _

from creme import persons
from creme.creme_core.gui.custom_form import CustomFormDescriptor
from creme.persons.forms.address import AddressesGroup
from creme.persons.forms.contact import BaseContactCustomForm

Contact = persons.get_contact_model()
Organisation = persons.get_organisation_model()

CONTACT_CREATION_CFORM = CustomFormDescriptor(
    id='persons-contact_creation',
    model=Contact,
    verbose_name=_('Creation form for contact'),
    base_form_class=BaseContactCustomForm,
    extra_group_classes=[AddressesGroup],
)
CONTACT_EDITION_CFORM = CustomFormDescriptor(
    id='persons-contact_edition',
    model=Contact,
    verbose_name=_('Edition form for contact'),
    base_form_class=BaseContactCustomForm,
    extra_group_classes=[AddressesGroup],
)
ORGANISATION_CREATION_CFORM = CustomFormDescriptor(
    id='persons-organisation_creation',
    model=Organisation,
    verbose_name=_('Creation form for organisation'),
    extra_group_classes=[AddressesGroup],
)
ORGANISATION_EDITION_CFORM = CustomFormDescriptor(
    id='persons-organisation_edition',
    model=Organisation,
    verbose_name=_('Edition form for organisation'),
    extra_group_classes=[AddressesGroup],
)

del Contact
del Organisation
