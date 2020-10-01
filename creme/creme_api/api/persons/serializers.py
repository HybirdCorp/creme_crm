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

from rest_framework import serializers

from creme.creme_api.api.serializers import (
    CremeEntityRelatedField,
    CremeEntitySerializer,
)
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


class ContactSerializer(CremeEntitySerializer):
    class Meta(CremeEntitySerializer.Meta):
        model = get_contact_model()
        fields = CremeEntitySerializer.Meta.fields + [
            'billing_address',
            'shipping_address',
            'civility',
            'last_name',
            'first_name',
            'skype',
            'phone',
            'mobile',
            'fax',
            'email',
            'url_site',
            'position',
            'full_position',
            'sector',
            'is_user',
            'birthday',
            'image',
        ]


class OrganisationSerializer(CremeEntitySerializer):
    class Meta:
        model = get_organisation_model()
        fields = CremeEntitySerializer.Meta.fields + [
            'billing_address',
            'shipping_address',
            'name',
            'is_managed',
            'phone',
            'fax',
            'email',
            'url_site',
            'sector',
            'legal_form',
            'staff_size',
            'capital',
            'annual_revenue',
            'siren',
            'naf',
            'siret',
            'rcs',
            'tvaintra',
            'subject_to_vat',
            'creation_date',
            'image',
        ]


class AddressSerializer(serializers.ModelSerializer):
    owner = CremeEntityRelatedField()

    class Meta:
        model = get_address_model()
        fields = [
            'id',
            'name',
            'address',
            'po_box',
            'zipcode',
            'city',
            'department',
            'state',
            'country',
            'owner',
        ]


class CivilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Civility
        fields = ['id', 'title', 'shortcut']


class PositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Position
        fields = ['id', 'title']


class StaffSizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = StaffSize
        fields = ['id', 'size']


class LegalFormSerializer(serializers.ModelSerializer):
    class Meta:
        model = LegalForm
        fields = ['id', 'title']


class SectorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sector
        fields = ['id', 'title']
