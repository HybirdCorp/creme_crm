from django.db import transaction
from django.utils.translation import gettext as _
from rest_framework import serializers

from creme.creme_api.api.core.serializers import (  # CremeEntityRelatedField,
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

Address = get_address_model()


# class AddressSerializer(serializers.ModelSerializer):
#     owner = CremeEntityRelatedField()
#
#     class Meta:
#         model = Address
#         fields = [
#             'id',
#             'name',
#             'address',
#             'po_box',
#             'zipcode',
#             'city',
#             'department',
#             'state',
#             'country',
#             'owner',
#         ]


class InnerAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = [
            "address",
            "po_box",
            "zipcode",
            "city",
            "department",
            "state",
            "country",
        ]


class CivilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Civility
        fields = ["id", "title", "shortcut"]


class PositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Position
        fields = ["id", "title"]


class StaffSizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = StaffSize
        fields = ["id", "size"]


class LegalFormSerializer(serializers.ModelSerializer):
    class Meta:
        model = LegalForm
        fields = ["id", "title"]


class SectorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sector
        fields = ["id", "title"]


class PersonWithAddressesMixin(serializers.Serializer):
    billing_address = InnerAddressSerializer(required=False)
    shipping_address = InnerAddressSerializer(required=False)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if "billing_address" in data and data["billing_address"] is None:
            data.pop("billing_address")
        if "shipping_address" in data and data["shipping_address"] is None:
            data.pop("shipping_address")
        return data

    @transaction.atomic
    def create(self, validated_data):
        billing_address_data = validated_data.pop("billing_address", None)
        shipping_address_data = validated_data.pop("shipping_address", None)
        instance = super().create(validated_data)
        save = False
        if billing_address_data is not None:
            save = True
            instance.billing_address = self.fields["billing_address"].create(
                {
                    **billing_address_data,
                    "owner": instance,
                    "name": _("Billing address"),
                }
            )
        if shipping_address_data is not None:
            save = True
            instance.shipping_address = self.fields["shipping_address"].create(
                {
                    **shipping_address_data,
                    "owner": instance,
                    "name": _("Shipping address"),
                }
            )
        if save:
            instance.save()
        return instance

    @transaction.atomic
    def update(self, instance, validated_data):
        billing_address_data = validated_data.pop("billing_address", None)
        shipping_address_data = validated_data.pop("shipping_address", None)
        if billing_address_data is not None:
            if instance.billing_address_id is not None:
                self.fields["billing_address"].update(
                    instance.billing_address,
                    {
                        **billing_address_data,
                        "name": _("Billing address"),
                    },
                )
            else:
                instance.billing_address = self.fields["billing_address"].create(
                    {
                        **billing_address_data,
                        "owner": instance,
                        "name": _("Billing address"),
                    }
                )
        if shipping_address_data is not None:
            if instance.shipping_address_id is not None:
                self.fields["shipping_address"].update(
                    instance.shipping_address,
                    {
                        **shipping_address_data,
                        "name": _("Shipping address"),
                    },
                )
            else:
                instance.shipping_address = self.fields["shipping_address"].create(
                    {
                        **shipping_address_data,
                        "owner": instance,
                        "name": _("Shipping address"),
                    }
                )
        return super().update(instance, validated_data)


class ContactSerializer(PersonWithAddressesMixin, CremeEntitySerializer):
    class Meta(CremeEntitySerializer.Meta):
        model = get_contact_model()
        fields = CremeEntitySerializer.Meta.fields + [
            "billing_address",
            "shipping_address",
            "civility",
            "last_name",
            "first_name",
            "skype",
            "phone",
            "mobile",
            "fax",
            "email",
            "url_site",
            "position",
            "full_position",
            "sector",
            "is_user",
            "birthday",
            # 'image',  # Need documents
        ]


class OrganisationSerializer(PersonWithAddressesMixin, CremeEntitySerializer):
    class Meta:
        model = get_organisation_model()
        fields = CremeEntitySerializer.Meta.fields + [
            "billing_address",
            "shipping_address",
            "name",
            "is_managed",
            "phone",
            "fax",
            "email",
            "url_site",
            "sector",
            "legal_form",
            "staff_size",
            "capital",
            "annual_revenue",
            "siren",
            "naf",
            "siret",
            "rcs",
            "tvaintra",
            "subject_to_vat",
            "creation_date",
            # 'image',
        ]
