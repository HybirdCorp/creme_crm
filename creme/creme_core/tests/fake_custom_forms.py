# -*- coding: utf-8 -*-

from creme.creme_core import models
from creme.creme_core.gui.custom_form import CustomFormDescriptor

from . import fake_forms

FAKEORGANISATION_CREATION_CFORM = CustomFormDescriptor(
    id='creme_core-fakeorganisation_creation',
    model=models.FakeOrganisation,
    verbose_name='Creation form for FakeOrganisation',
    extra_group_classes=[fake_forms.FakeAddressGroup],
)

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
)
