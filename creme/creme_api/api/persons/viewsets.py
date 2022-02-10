from rest_framework import mixins, viewsets

from creme import persons
from creme.creme_api.api.schemas import CremeSchema

from .serializers import ContactSerializer

Contact = persons.get_contact_model()


class ContactViewSet(mixins.CreateModelMixin,
                     mixins.RetrieveModelMixin,
                     mixins.UpdateModelMixin,
                     mixins.DestroyModelMixin,
                     mixins.ListModelMixin,
                     viewsets.GenericViewSet):
    """
    create:
    POST /contacts

    retrieve:
    GET /contacts/{userId}

    update:
    PUT /contacts/{userId}

    partial_update:
    PATCH /contacts/{userId}

    list:
    GET /contacts

    """
    queryset = Contact.objects.all()
    serializer_class = ContactSerializer
    schema = CremeSchema(tags=["Contacts"], operation_id_base="Contacts")
