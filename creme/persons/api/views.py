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

from rest_framework import viewsets

from creme.persons.models import (
    Address,
    Civility,
    Contact,
    LegalForm,
    Organisation,
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


class ContactViewSet(viewsets.ModelViewSet):
    queryset = Contact.objects.all()
    serializer_class = ContactSerializer


class OrganisationViewSet(viewsets.ModelViewSet):
    queryset = Organisation.objects.all()
    serializer_class = OrganisationSerializer


class AddressViewSet(viewsets.ModelViewSet):
    queryset = Address.objects.all()
    serializer_class = AddressSerializer


class CivilityViewSet(viewsets.ModelViewSet):
    queryset = Civility.objects.all()
    serializer_class = CivilitySerializer


class PositionViewSet(viewsets.ModelViewSet):
    queryset = Position.objects.all()
    serializer_class = PositionSerializer


class StaffSizeViewSet(viewsets.ModelViewSet):
    queryset = StaffSize.objects.all()
    serializer_class = StaffSizeSerializer


class LegalFormViewSet(viewsets.ModelViewSet):
    queryset = LegalForm.objects.all()
    serializer_class = LegalFormSerializer


class SectorViewSet(viewsets.ModelViewSet):
    queryset = Sector.objects.all()
    serializer_class = SectorSerializer
