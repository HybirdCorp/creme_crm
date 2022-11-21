from creme.creme_core import models
from creme.creme_core.gui.custom_form import (
    LAYOUT_DUAL_FIRST,
    LAYOUT_DUAL_SECOND,
    LAYOUT_REGULAR,
    CustomFormDefault,
    CustomFormDescriptor,
    EntityCellCustomFormSpecial,
)

from . import fake_forms


class FakeOrganisationCreationFormDefault(CustomFormDefault):
    def groups_desc(self):
        return [
            {
                'name': 'General',
                'cells': [
                    *self.regular_fields_cells('user', 'name', 'sector'),
                    # (
                    #     EntityCellCustomFormSpecial,
                    #     {'name': EntityCellCustomFormSpecial.REMAINING_REGULARFIELDS},
                    # ),
                ],
            },
            fake_forms.FakeAddressGroup(model=self.descriptor.model),
        ]


class FakeOrganisationEditionFormDefault(CustomFormDefault):
    def groups_desc(self):
        return [
            {
                'name': 'General',
                'cells': [
                    *self.regular_fields_cells('user', 'name', 'sector'),
                    # (
                    #     EntityCellCustomFormSpecial,
                    #     {'name': EntityCellCustomFormSpecial.REMAINING_REGULARFIELDS},
                    # ),
                ],
            },
            # fake_forms.FakeAddressGroup(model=self.descriptor.model),
        ]


FAKEORGANISATION_CREATION_CFORM = CustomFormDescriptor(
    id='creme_core-fakeorganisation_creation',
    model=models.FakeOrganisation,
    verbose_name='Creation form for FakeOrganisation',
    extra_group_classes=[fake_forms.FakeAddressGroup],
    default=FakeOrganisationCreationFormDefault,
)
FAKEORGANISATION_EDITION_CFORM = CustomFormDescriptor(
    id='creme_core-fakeorganisation_edition',
    model=models.FakeOrganisation,
    form_type=CustomFormDescriptor.EDITION_FORM,
    verbose_name='Edition form for FakeOrganisation',
    extra_group_classes=[fake_forms.FakeAddressGroup],
    default=FakeOrganisationEditionFormDefault,
)


# ------------------------------------------------------------------------------
class FakeActivityCreationFormDefault(CustomFormDefault):
    def groups_desc(self):
        return [
            {
                'name': 'General',
                'cells': [
                    *self.regular_fields_cells(
                        'user', 'title', 'type',
                        # 'minutes',  # Not in the default config
                        # 'description',  # Excluded
                    ),
                    # (
                    #     EntityCellCustomFormSpecial,
                    #     {'name': EntityCellCustomFormSpecial.REMAINING_REGULARFIELDS},
                    # ),  # Should be used in regular populate scripts
                ],
                'layout': LAYOUT_DUAL_FIRST,
            }, {
                'name': 'Where & when',
                'cells': [
                    *self.regular_fields_cells('place'),
                    fake_forms.FakeActivityStartSubCell().into_cell(),
                    fake_forms.FakeActivityEndSubCell().into_cell(),
                ],
                'layout': LAYOUT_DUAL_SECOND,
            },
            self.group_desc_for_customfields(layout=LAYOUT_REGULAR),
        ]


class FakeActivityEditionFormDefault(CustomFormDefault):
    def groups_desc(self):
        return [
            {
                'name': 'General',
                'cells': [
                    *self.regular_fields_cells('user', 'title', 'type'),
                    (
                        EntityCellCustomFormSpecial,
                        {'name': EntityCellCustomFormSpecial.REMAINING_REGULARFIELDS},
                    ),
                ],
            }, {
                'name': 'Where & when',
                'cells': [
                    *self.regular_fields_cells('place'),
                    fake_forms.FakeActivityStartSubCell().into_cell(),
                    fake_forms.FakeActivityEndSubCell().into_cell(),
                ],
            },
        ]


FAKEACTIVITY_CREATION_CFORM = CustomFormDescriptor(
    id='creme_core-fakeactivity_creation',
    model=models.FakeActivity,
    verbose_name='Creation form for FakeActivity',
    base_form_class=fake_forms.BaseFakeActivityCustomForm,
    excluded_fields=['description', 'start', 'end'],
    extra_sub_cells=[
        fake_forms.FakeActivityStartSubCell(),
        fake_forms.FakeActivityEndSubCell(),
    ],
    default=FakeActivityCreationFormDefault,
)
FAKEACTIVITY_EDITION_CFORM = CustomFormDescriptor(
    id='creme_core-fakeactivity_edition',
    model=models.FakeActivity,
    form_type=CustomFormDescriptor.EDITION_FORM,
    verbose_name='Edition form for FakeActivity',
    base_form_class=fake_forms.BaseFakeActivityCustomForm,
    excluded_fields=['description', 'start', 'end'],
    extra_sub_cells=[
        fake_forms.FakeActivityStartSubCell(),
        fake_forms.FakeActivityEndSubCell(),
    ],
    default=FakeActivityEditionFormDefault,
)
