# -*- coding: utf-8 -*-

from django import forms

from .. import forms as core_forms
from ..forms.mass_import import ImportForm4CremeEntity, extractorfield_factory
from ..forms.merge import MergeEntitiesBaseForm
from ..gui.custom_form import CustomFormExtraSubCell, ExtraFieldGroup
from . import fake_models


class FakeContactQuickForm(core_forms.CremeEntityQuickForm):
    class Meta:
        model = fake_models.FakeContact
        fields = ('user', 'last_name', 'first_name', 'phone', 'email')


class FakeAddressGroup(ExtraFieldGroup):
    extra_group_id = 'test-address'
    name = 'Address'

    # NB: currently used in creme_config only.
    # def formfields(self, ...):
    # def save(self, ...):


class FakeContactForm(core_forms.CremeEntityForm):
    class Meta:
        model = fake_models.FakeContact
        fields = '__all__'


class FakeOrganisationQuickForm(core_forms.CremeEntityQuickForm):
    class Meta:
        model = fake_models.FakeOrganisation
        fields = ('name', 'user')


class FakeOrganisationForm(core_forms.CremeEntityForm):
    class Meta:
        model = fake_models.FakeOrganisation
        fields = '__all__'


class FakeAddressForm(core_forms.CremeModelForm):
    class Meta:
        model = fake_models.FakeAddress
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
        user = self.user

        for field_name in _ADDR_FIELD_NAMES:
            extr_value, err_msg = data[_ADDRESS_PREFIX + field_name].extract_value(
                line=line, user=user,
            )
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
                instance.address = fake_models.FakeAddress.objects.create(**address_dict)
                instance.save()


# Activity ---
class _FakeActivitySubCell(CustomFormExtraSubCell):
    def __init__(self, model=fake_models.FakeActivity):
        super().__init__(model=model)


class FakeActivityStartSubCell(_FakeActivitySubCell):
    sub_type_id = 'fakeactivity_start'
    verbose_name = 'Start'

    def formfield(self, instance, user, **kwargs):
        return forms.DateTimeField(label='Start', **kwargs)


class FakeActivityEndSubCell(_FakeActivitySubCell):
    sub_type_id = 'fakeactivity_end'
    verbose_name = 'End'
    is_required = False

    def formfield(self, instance, user, **kwargs):
        return forms.DateTimeField(label='End', **kwargs)


class BaseFakeActivityCustomForm(core_forms.CremeEntityForm):
    def save(self, *args, **kwargs):
        instance = self.instance
        cdata = self.cleaned_data

        instance.start = cdata[FakeActivityStartSubCell().into_cell().key]
        instance.end = cdata.get(FakeActivityEndSubCell().into_cell().key)

        return super().save(*args, **kwargs)


# ---


def get_csv_form_builder(header_dict, choices):
    get_field = fake_models.FakeAddress._meta.get_field
    attrs = {
        _ADDRESS_PREFIX + field_name: extractorfield_factory(
            get_field(field_name), header_dict, choices,
        ) for field_name in _ADDR_FIELD_NAMES
    }

    return type('PersonCSVImportForm', (_FakePersonCSVImportForm,), attrs)


def get_merge_form_builder():
    return MergeEntitiesBaseForm


class FakeEmailCampaignForm(core_forms.CremeEntityForm):
    class Meta:
        model = fake_models.FakeEmailCampaign
        fields = '__all__'


class FakeProductForm(core_forms.CremeEntityForm):
    class Meta:
        model = fake_models.FakeProduct
        fields = '__all__'
