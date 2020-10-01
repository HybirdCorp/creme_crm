# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2020  Hybird
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

from rest_framework.schemas.openapi import AutoSchema

from creme.creme_api.api.viewsets import CremeEntityViewSet, CremeModelViewSet
from creme.persons import (
    get_address_model,
    get_contact_model,
    get_organisation_model,
)
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

schema = AutoSchema(tags=['Persons'])


class ContactViewSet(CremeEntityViewSet):
    queryset = get_contact_model().objects.all()
    serializer_class = ContactSerializer
    schema = schema


class OrganisationViewSet(CremeEntityViewSet):
    queryset = get_organisation_model().objects.all()
    serializer_class = OrganisationSerializer
    schema = schema


class AddressViewSet(CremeModelViewSet):
    queryset = get_address_model().objects.all()
    serializer_class = AddressSerializer
    schema = schema


class CivilityViewSet(CremeModelViewSet):
    queryset = Civility.objects.all()
    serializer_class = CivilitySerializer
    schema = schema


class PositionViewSet(CremeModelViewSet):
    queryset = Position.objects.all()
    serializer_class = PositionSerializer
    schema = schema


class StaffSizeViewSet(CremeModelViewSet):
    queryset = StaffSize.objects.all()
    serializer_class = StaffSizeSerializer
    schema = schema


class LegalFormViewSet(CremeModelViewSet):
    queryset = LegalForm.objects.all()
    serializer_class = LegalFormSerializer
    schema = schema


class SectorViewSet(CremeModelViewSet):
    queryset = Sector.objects.all()
    serializer_class = SectorSerializer
    schema = schema
