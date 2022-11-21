from django.utils.translation import gettext_lazy as _

import creme.recurrents.forms.recurrentgenerator as base
from creme import recurrents
from creme.creme_core.gui.custom_form import (
    CustomFormDefault,
    CustomFormDescriptor,
)

RecurrentGenerator = recurrents.get_rgenerator_model()


class GeneratorCreationFormDescriptor(CustomFormDefault):
    CTYPE = 'CTYPE'
    sub_cells = {CTYPE: base.GeneratorCTypeSubCell}
    main_fields = ['user', 'name', CTYPE, 'first_generation', 'periodicity']


class GeneratorEditionFormDescriptor(CustomFormDefault):
    main_fields = ['user', 'name', 'first_generation', 'periodicity']


GENERATOR_CREATION_CFORM = CustomFormDescriptor(
    id='recurrents-generator_creation',
    model=RecurrentGenerator,
    verbose_name=_('Creation form for generator'),
    base_form_class=base.BaseRecurrentGeneratorCustomForm,
    extra_sub_cells=[base.GeneratorCTypeSubCell(model=RecurrentGenerator)],
    default=GeneratorCreationFormDescriptor,
)
GENERATOR_EDITION_CFORM = CustomFormDescriptor(
    id='recurrents-generator_edition',
    model=RecurrentGenerator,
    form_type=CustomFormDescriptor.EDITION_FORM,
    verbose_name=_('Edition form for generator'),
    base_form_class=base.BaseRecurrentGeneratorCustomForm,
    default=GeneratorEditionFormDescriptor,
)

del RecurrentGenerator
