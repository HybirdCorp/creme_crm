from django.utils.translation import gettext_lazy as _

from creme import commercial
from creme.creme_core.gui.custom_form import (
    CustomFormDefault,
    CustomFormDescriptor,
)

Act = commercial.get_act_model()
Pattern = commercial.get_pattern_model()
Strategy = commercial.get_strategy_model()


# ------------------------------------------------------------------------------
class ActFormDeFault(CustomFormDefault):
    main_fields = [
        'user', 'name',
        'expected_sales', 'cost', 'goal',
        'start', 'due_date',
        'act_type',
        'segment',
    ]


ACT_CREATION_CFORM = CustomFormDescriptor(
    id='commercial-act_creation',
    model=Act,
    verbose_name=_('Creation form for commercial action'),
    default=ActFormDeFault,
)
ACT_EDITION_CFORM = CustomFormDescriptor(
    id='commercial-act_edition',
    model=Act,
    form_type=CustomFormDescriptor.EDITION_FORM,
    verbose_name=_('Edition form for commercial action'),
    default=ActFormDeFault,
)


# ------------------------------------------------------------------------------
class ActObjectivePatternFormDefault(CustomFormDefault):
    main_fields = ['user', 'name', 'average_sales', 'segment']


PATTERN_CREATION_CFORM = CustomFormDescriptor(
    id='commercial-objective_pattern_creation',
    model=Pattern,
    verbose_name=_('Creation Form for objective pattern'),
    default=ActObjectivePatternFormDefault,
)
PATTERN_EDITION_CFORM = CustomFormDescriptor(
    id='commercial-objective_pattern_edition',
    model=Pattern,
    form_type=CustomFormDescriptor.EDITION_FORM,
    verbose_name=_('Edition Form for objective pattern'),
    default=ActObjectivePatternFormDefault,
)


# ------------------------------------------------------------------------------
class StrategyFormDefault(CustomFormDefault):
    main_fields = ['user', 'name']


STRATEGY_CREATION_CFORM = CustomFormDescriptor(
    id='commercial-strategy_creation',
    model=Strategy,
    verbose_name=_('Creation form for commercial strategy'),
    default=StrategyFormDefault,
)
STRATEGY_EDITION_CFORM = CustomFormDescriptor(
    id='commercial-strategy_edition',
    model=Strategy,
    form_type=CustomFormDescriptor.EDITION_FORM,
    verbose_name=_('Edition form for commercial strategy'),
    default=StrategyFormDefault,
)

del Act
del Pattern
del Strategy
