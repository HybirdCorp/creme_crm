# -*- coding: utf-8 -*-

from django.utils.translation import gettext_lazy as _

from creme import commercial
from creme.creme_core.gui.custom_form import CustomFormDescriptor

Act = commercial.get_act_model()
Pattern = commercial.get_pattern_model()
Strategy = commercial.get_strategy_model()

ACT_CREATION_CFORM = CustomFormDescriptor(
    id='commercial-act_creation',
    model=Act,
    verbose_name=_('Creation form for commercial action'),
)
ACT_EDITION_CFORM = CustomFormDescriptor(
    id='commercial-act_edition',
    model=Act,
    form_type=CustomFormDescriptor.EDITION_FORM,
    verbose_name=_('Edition form for commercial action'),
)
PATTERN_CREATION_CFORM = CustomFormDescriptor(
    id='commercial-objective_pattern_creation',
    model=Pattern,
    verbose_name=_('Creation Form for objective pattern'),
)
PATTERN_EDITION_CFORM = CustomFormDescriptor(
    id='commercial-objective_pattern_edition',
    model=Pattern,
    form_type=CustomFormDescriptor.EDITION_FORM,
    verbose_name=_('Edition Form for objective pattern'),
)
STRATEGY_CREATION_CFORM = CustomFormDescriptor(
    id='commercial-strategy_creation',
    model=Strategy,
    verbose_name=_('Creation form for commercial strategy'),
)
STRATEGY_EDITION_CFORM = CustomFormDescriptor(
    id='commercial-strategy_edition',
    model=Strategy,
    form_type=CustomFormDescriptor.EDITION_FORM,
    verbose_name=_('Edition form for commercial strategy'),
)

del Act
del Pattern
del Strategy
