from creme import persons
from creme.creme_api.api.core.viewsets import (
    CremeEntityViewSet,
    CremeModelViewSet,
)
from creme.creme_api.api.schemas import CremeSchema
from creme.persons.models.other_models import (
    Civility,
    LegalForm,
    Position,
    Sector,
    StaffSize,
)

from .serializers import (
    AddressSerializer,
    CivilitySerializer,
    ContactSerializer,
    LegalFormSerializer,
    OrganisationSerializer,
    PositionSerializer,
    SectorSerializer,
    StaffSizeSerializer,
)


class ContactViewSet(CremeEntityViewSet):
    """
    create:
    Create a contact.

    retrieve:
    Retrieve a contact.

    update:
    Update a contact.

    partial_update:
    Partially update a contact.

    list:
    List contacts.

    delete:
    Delete a contact.

    trash:
    Move a contact to the trash.

    restore:
    Restore a contact from the trash.

    clone:
    Clone a contact.

    """
    queryset = persons.get_contact_model().objects.select_related(
        'billing_address', 'shipping_address')
    serializer_class = ContactSerializer
    schema = CremeSchema(tags=["Contacts"])


class OrganisationViewSet(CremeEntityViewSet):
    """
    create:
    Create an organisation.

    retrieve:
    Retrieve an organisation.

    update:
    Update an organisation.

    partial_update:
    Partially update an organisation.

    list:
    List organisations.

    delete:
    Delete an organisation.

    trash:
    Move an organisation to the trash.

    restore:
    Restore an organisation from the trash.

    clone:
    Clone an organisation.

    """
    queryset = persons.get_organisation_model().objects.all()
    serializer_class = OrganisationSerializer
    schema = CremeSchema(tags=["Organisations"])


class CivilityViewSet(CremeModelViewSet):
    """
    create:
    Create a civility.

    retrieve:
    Retrieve a civility.

    update:
    Update a civility.

    partial_update:
    Partially update a civility.

    list:
    List civilities.

    delete:
    Delete a civility

    """
    queryset = Civility.objects.all()
    serializer_class = CivilitySerializer
    schema = CremeSchema(tags=["Civilities"])


class PositionViewSet(CremeModelViewSet):
    """
    create:
    Create a position.

    retrieve:
    Retrieve a position.

    update:
    Update a position.

    partial_update:
    Partially update a position.

    list:
    List positions.

    delete:
    Delete a position

    """
    queryset = Position.objects.all()
    serializer_class = PositionSerializer
    schema = CremeSchema(tags=["Positions"])


class StaffSizeViewSet(CremeModelViewSet):
    """
    create:
    Create a staff size.

    retrieve:
    Retrieve a staff size.

    update:
    Update a staff size.

    partial_update:
    Partially update a staff size.

    list:
    List staff sizes.

    delete:
    Delete a staff size

    """
    queryset = StaffSize.objects.all()
    serializer_class = StaffSizeSerializer
    schema = CremeSchema(tags=["Staff sizes"])


class LegalFormViewSet(CremeModelViewSet):
    """
    create:
    Create a legal form.

    retrieve:
    Retrieve a legal form.

    update:
    Update a legal form.

    partial_update:
    Partially update a legal form.

    list:
    List legal forms.

    delete:
    Delete a legal form

    """
    queryset = LegalForm.objects.all()
    serializer_class = LegalFormSerializer
    schema = CremeSchema(tags=["Legal forms"])


class SectorViewSet(CremeModelViewSet):
    """
    create:
    Create a sector.

    retrieve:
    Retrieve a sector.

    update:
    Update a sector.

    partial_update:
    Partially update a sector.

    list:
    List sectors.

    delete:
    Delete a sector

    """
    queryset = Sector.objects.all()
    serializer_class = SectorSerializer
    schema = CremeSchema(tags=["Sectors"])
