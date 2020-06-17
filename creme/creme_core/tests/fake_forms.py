# -*- coding: utf-8 -*-

from .. import forms
from ..forms.mass_import import ImportForm4CremeEntity, extractorfield_factory
from ..forms.merge import MergeEntitiesBaseForm
from .fake_models import (
    FakeAddress,
    FakeContact,
    FakeEmailCampaign,
    FakeOrganisation,
    FakeProduct,
)


class FakeContactQuickForm(forms.CremeEntityQuickForm):
    class Meta:
        model = FakeContact
        fields = ('user', 'last_name', 'first_name', 'phone', 'email')


class FakeContactForm(forms.CremeEntityForm):
    class Meta:
        model = FakeContact
        fields = '__all__'


class FakeOrganisationQuickForm(forms.CremeEntityQuickForm):
    class Meta:
        model = FakeOrganisation
        fields = ('name', 'user')


class FakeOrganisationForm(forms.CremeEntityForm):
    class Meta:
        model = FakeOrganisation
        fields = '__all__'


class FakeAddressForm(forms.CremeModelForm):
    class Meta:
        model = FakeAddress
        fields = '__all__'

    def __init__(self, entity, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.entity = entity


_ADDRESS_PREFIX = 'address_'
_ADDR_FIELD_NAMES = ('value', 'zipcode', 'city', 'department', 'country')


class _FakePersonCSVImportForm(ImportForm4CremeEntity):
    class Meta:
        exclude = ('image',)

    def _post_instance_creation(self, instance, line, updated):
        super()._post_instance_creation(instance, line, updated)
        data = self.cleaned_data
        address_dict = {}

        for field_name in _ADDR_FIELD_NAMES:
            extr_value, err_msg = data[_ADDRESS_PREFIX + field_name].extract_value(line)
            if extr_value:
                address_dict[field_name] = extr_value

            self.append_error(err_msg)

        if address_dict:
            address_dict['entity'] = instance
            address = instance.address

            if address is not None:  # Update
                for fname, fvalue in address_dict.items():
                    setattr(address, fname, fvalue)
                address.save()
            else:
                instance.address = FakeAddress.objects.create(**address_dict)
                instance.save()


def get_csv_form_builder(header_dict, choices):
    get_field = FakeAddress._meta.get_field
    attrs = {
        _ADDRESS_PREFIX + field_name: extractorfield_factory(
            get_field(field_name), header_dict, choices,
        ) for field_name in _ADDR_FIELD_NAMES
    }

    return type('PersonCSVImportForm', (_FakePersonCSVImportForm,), attrs)


def get_merge_form_builder():
    return MergeEntitiesBaseForm


class FakeEmailCampaignForm(forms.CremeEntityForm):
    class Meta:
        model = FakeEmailCampaign
        fields = '__all__'


class FakeProductForm(forms.CremeEntityForm):
    class Meta:
        model = FakeProduct
        fields = '__all__'
