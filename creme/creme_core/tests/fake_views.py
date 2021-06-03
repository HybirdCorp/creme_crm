# -*- coding: utf-8 -*-

from creme.creme_core.views import generic

from ..tests import fake_forms, fake_models
from . import fake_custom_forms


class FakeDocumentsList(generic.EntitiesList):
    model = fake_models.FakeDocument


class FakeImageDetail(generic.EntityDetail):
    model = fake_models.FakeImage
    pk_url_kwarg = 'image_id'


class FakeImagesList(generic.EntitiesList):
    model = fake_models.FakeImage


class FakeContactCreation(generic.EntityCreation):
    model = fake_models.FakeContact
    form_class = fake_forms.FakeContactForm


class FakeContactEdition(generic.EntityEdition):
    model = fake_models.FakeContact
    form_class = fake_forms.FakeContactForm
    pk_url_kwarg = 'contact_id'


class FakeContactDetail(generic.EntityDetail):
    model = fake_models.FakeContact
    # template_name = 'creme_core/tests/view-fake-contact.html'  TODO ?
    pk_url_kwarg = 'contact_id'


class FakeContactsList(generic.EntitiesList):
    model = fake_models.FakeContact
    # default_headerfilter_id = DEFAULT_HFILTER_FAKE_CONTACT TODO ?


class FakeOrganisationCreation(generic.EntityCreation):
    model = fake_models.FakeOrganisation
    form_class = fake_forms.FakeOrganisationForm


class FakeOrganisationEdition(generic.EntityEdition):
    model = fake_models.FakeOrganisation
    form_class = fake_forms.FakeOrganisationForm
    pk_url_kwarg = 'orga_id'


class FakeOrganisationDetail(generic.EntityDetail):
    model = fake_models.FakeOrganisation
    # template_name = 'creme_core/tests/view-fake-organisation.html'  TODO ?
    pk_url_kwarg = 'orga_id'


class FakeOrganisationsList(generic.EntitiesList):
    model = fake_models.FakeOrganisation


class FakeAddressCreation(generic.AddingInstanceToEntityPopup):
    model = fake_models.FakeAddress
    form_class = fake_forms.FakeAddressForm
    title = 'Adding address to <{entity}>'


class FakeAddressEdition(generic.RelatedToEntityEditionPopup):
    model = fake_models.FakeAddress
    pk_url_kwarg = 'address_id'
    form_class = fake_forms.FakeAddressForm
    title = 'Address for <{entity}>'


class FakeActivityCreation(generic.EntityCreation):
    model = fake_models.FakeActivity
    form_class = fake_custom_forms.FAKEACTIVITY_CREATION_CFORM


class FakeActivityEdition(generic.EntityEdition):
    model = fake_models.FakeActivity
    form_class = fake_custom_forms.FAKEACTIVITY_EDITION_CFORM
    pk_url_kwarg = 'activity_id'


class FakeActivitiesList(generic.EntitiesList):
    model = fake_models.FakeActivity


class FakeEmailCampaignsList(generic.EntitiesList):
    model = fake_models.FakeEmailCampaign


class FakeInvoiceDetail(generic.EntityDetail):
    model = fake_models.FakeInvoice
    pk_url_kwarg = 'invoice_id'


class FakeInvoicesList(generic.EntitiesList):
    model = fake_models.FakeInvoice


class FakeInvoiceLinesList(generic.EntitiesList):
    model = fake_models.FakeInvoiceLine

    def get_show_actions(self):
        return False


class FakeMailingListsList(generic.EntitiesList):
    model = fake_models.FakeMailingList


class FakeMailingListDetail(generic.EntityDetail):
    model = fake_models.FakeMailingList
    pk_url_kwarg = 'ml_id'
