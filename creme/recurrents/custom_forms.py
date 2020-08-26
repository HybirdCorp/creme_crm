# -*- coding: utf-8 -*-

from django.utils.translation import gettext_lazy as _

from creme import recurrents
from creme.creme_core.gui.custom_form import CustomFormDescriptor
from creme.recurrents.forms import recurrentgenerator as base

RecurrentGenerator = recurrents.get_rgenerator_model()

GENERATOR_CREATION_CFORM = CustomFormDescriptor(
    id='recurrents-generator_creation',
    model=RecurrentGenerator,
    verbose_name=_('Creation form for generator'),
    base_form_class=base.BaseRecurrentGeneratorCustomForm,
    extra_sub_cells=[base.GeneratorCTypeSubCell(model=RecurrentGenerator)],
)
GENERATOR_EDITION_CFORM = CustomFormDescriptor(
    id='recurrents-generator_edition',
    model=RecurrentGenerator,
    form_type=CustomFormDescriptor.EDITION_FORM,
    verbose_name=_('Edition form for generator'),
    base_form_class=base.BaseRecurrentGeneratorCustomForm,
)

del RecurrentGenerator
