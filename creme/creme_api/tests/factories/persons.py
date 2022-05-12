import factory
from django.utils.translation import gettext as _
from factory.django import DjangoModelFactory

from creme import persons
from creme.persons.models import (
    Address,
    Civility,
    LegalForm,
    Position,
    Sector,
    StaffSize,
)

from .auth import UserFactory, build_email, build_username


class CivilityFactory(DjangoModelFactory):
    title = "Captain"
    shortcut = "Cpt"

    class Meta:
        model = Civility


class PositionFactory(DjangoModelFactory):
    title = "Captain"

    class Meta:
        model = Position


class SectorFactory(DjangoModelFactory):
    title = "Industry"

    class Meta:
        model = Sector


class AddressFactory(DjangoModelFactory):
    name = "Address Name"
    address = "1 Main Street"
    po_box = "PO123"
    zipcode = "ZIP123"
    city = "City"
    department = "Dept"
    state = "State"
    country = "Country"

    owner = None  # Generic Relation; must be provided
    # content_type = factory.LazyAttribute(
    #     lambda o: get_content_type(o.owner)
    # )
    # object_id = factory.SelfAttribute('owner.id')

    class Meta:
        model = Address


class PersonWithAddressesMixin(DjangoModelFactory):
    @factory.post_generation
    def billing_address(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted is True or kwargs:
            kwargs["owner"] = self
            self.billing_address = AddressFactory(
                **{"name": _("Billing address"), **kwargs}
            )

    @factory.post_generation
    def shipping_address(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted is True or kwargs:
            kwargs["owner"] = self
            self.shipping_address = AddressFactory(
                **{"name": _("Shipping address"), **kwargs}
            )


def build_url_site(user):
    return "https://www.%s.provider.com" % build_username(user)


class ContactFactory(PersonWithAddressesMixin, DjangoModelFactory):
    user = factory.SubFactory(UserFactory)
    description = "Description"

    first_name = "Jean"
    last_name = "Dupont"
    skype = "jean.dupont"
    phone = "+330100000000"
    mobile = "+330600000000"
    fax = "+330100000001"
    email = factory.lazy_attribute(build_email)
    url_site = factory.lazy_attribute(build_url_site)
    full_position = "Full position"
    birthday = "2000-01-01"

    civility = factory.SubFactory(CivilityFactory)
    position = factory.SubFactory(PositionFactory)
    sector = factory.SubFactory(SectorFactory)

    class Meta:
        model = persons.get_contact_model()


class LegalFormFactory(DjangoModelFactory):
    title = "Trust"

    class Meta:
        model = LegalForm


class StaffSizeFactory(DjangoModelFactory):
    size = "1 - 10"

    class Meta:
        model = StaffSize


class OrganisationFactory(PersonWithAddressesMixin, DjangoModelFactory):
    user = factory.SubFactory(UserFactory)
    description = "Description"

    name = "Creme Organisation"
    phone = "+330100000000"
    fax = "+330100000001"
    email = "creme.organisation@provider.com"
    url_site = "https://www.creme.organisation.provider.com"
    capital = 50000
    annual_revenue = "1500000"
    siren = "001001001001"
    naf = "002002002002"
    siret = "003003003003"
    rcs = "004004004004"
    tvaintra = "005005005005"
    subject_to_vat = True
    creation_date = "2005-05-24"

    sector = factory.SubFactory(SectorFactory)
    legal_form = factory.SubFactory(LegalFormFactory)
    staff_size = factory.SubFactory(StaffSizeFactory)

    class Meta:
        model = persons.get_organisation_model()
