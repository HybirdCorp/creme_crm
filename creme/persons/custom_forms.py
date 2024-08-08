from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme import persons
from creme.creme_core.gui.custom_form import (
    LAYOUT_DUAL_SECOND,
    CustomFormDefault,
    CustomFormDescriptor,
)
from creme.persons.forms.address import AddressesGroup
from creme.persons.forms.contact import BaseContactCustomForm

Contact = persons.get_contact_model()
Organisation = persons.get_organisation_model()


class ContactFormDefault(CustomFormDefault):
    main_fields = [
        'user',
        'civility', 'last_name', 'first_name',
        'position', 'full_position',
        'sector',
        'birthday',
        'image',
        'languages',
    ]
    details_fields = ['skype', 'phone', 'mobile', 'fax', 'email', 'url_site']

    def groups_desc(self):
        return [
            # LAYOUT_DUAL_FIRST
            self.group_desc_for_main_fields(),

            # LAYOUT_DUAL_SECOND
            self.group_desc_for_description(),
            {
                'name': gettext('Contact details'),
                'layout': LAYOUT_DUAL_SECOND,
                'cells': [*self.regular_fields_cells(*self.details_fields)],
            },
            self.group_desc_for_customfields(),

            # LAYOUT_REGULAR
            AddressesGroup(model=self.descriptor.model),
            *self.groups_desc_for_properties_n_relations(),
        ]


CONTACT_CREATION_CFORM = CustomFormDescriptor(
    id='persons-contact_creation',
    model=Contact,
    verbose_name=_('Creation form for contact'),
    base_form_class=BaseContactCustomForm,
    extra_group_classes=[AddressesGroup],
    default=ContactFormDefault,
)
CONTACT_EDITION_CFORM = CustomFormDescriptor(
    id='persons-contact_edition',
    model=Contact,
    form_type=CustomFormDescriptor.EDITION_FORM,
    verbose_name=_('Edition form for contact'),
    base_form_class=BaseContactCustomForm,
    extra_group_classes=[AddressesGroup],
    default=ContactFormDefault,
)


# ------------------------------------------------------------------------------
class OrganisationFormDefault(CustomFormDefault):
    main_fields = [
        'user',
        'name',
        'phone', 'fax', 'email', 'url_site',
        'sector', 'legal_form', 'staff_size',
        'capital', 'annual_revenue',
        'code',
        'siren', 'naf', 'siret', 'rcs',
        'tvaintra', 'subject_to_vat',
        'creation_date',
        'image',
    ]

    def groups_desc(self):
        return [
            # LAYOUT_DUAL_FIRST
            self.group_desc_for_main_fields(),

            # LAYOUT_DUAL_SECOND
            self.group_desc_for_description(),
            self.group_desc_for_customfields(),

            # LAYOUT_REGULAR
            AddressesGroup(model=self.descriptor.model),
            *self.groups_desc_for_properties_n_relations(),
        ]


ORGANISATION_CREATION_CFORM = CustomFormDescriptor(
    id='persons-organisation_creation',
    model=Organisation,
    verbose_name=_('Creation form for organisation'),
    extra_group_classes=[AddressesGroup],
    default=OrganisationFormDefault,
)
ORGANISATION_EDITION_CFORM = CustomFormDescriptor(
    id='persons-organisation_edition',
    model=Organisation,
    form_type=CustomFormDescriptor.EDITION_FORM,
    verbose_name=_('Edition form for organisation'),
    extra_group_classes=[AddressesGroup],
    default=OrganisationFormDefault,
)

del Contact
del Organisation
