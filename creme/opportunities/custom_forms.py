from django.utils.translation import gettext_lazy as _

import creme.opportunities.forms.opportunity as opp_forms
from creme import opportunities
from creme.creme_core.gui.custom_form import (
    CustomFormDefault,
    CustomFormDescriptor,
)

Opportunity = opportunities.get_opportunity_model()


class _OpportunityFormDefault(CustomFormDefault):
    EMITTER = 'EMITTER'
    TARGET = 'target'
    sub_cells = {
        EMITTER: opp_forms.OppEmitterSubCell,
        TARGET:  opp_forms.OppTargetSubCell,
    }


class OpportunityCreationFormDescriptor(_OpportunityFormDefault):
    main_fields = [
        'user',
        'name',
        _OpportunityFormDefault.EMITTER,
        _OpportunityFormDefault.TARGET,
        'reference',
        'estimated_sales',
        'made_sales',
        'currency',
        'sales_phase',
        'chance_to_win',
        'expected_closing_date',
        'closing_date',
        'origin',
        'first_action_date',
    ]


class OpportunityEditionFormDefault(_OpportunityFormDefault):
    main_fields = [
        'user',
        'name',
        _OpportunityFormDefault.TARGET,
        'reference',
        'estimated_sales',
        'made_sales',
        'currency',
        'sales_phase',
        'chance_to_win',
        'expected_closing_date',
        'closing_date',
        'origin',
        'first_action_date',
    ]


OPPORTUNITY_CREATION_CFORM = CustomFormDescriptor(
    id='opportunities-opportunity_creation',
    model=Opportunity,
    verbose_name=_('Creation form for opportunity'),
    base_form_class=opp_forms.BaseCustomForm,
    extra_sub_cells=[
        opp_forms.OppEmitterSubCell(),
        opp_forms.OppTargetSubCell(),
    ],
    default=OpportunityCreationFormDescriptor,
)
OPPORTUNITY_EDITION_CFORM = CustomFormDescriptor(
    id='opportunities-opportunity_edition',
    model=Opportunity,
    form_type=CustomFormDescriptor.EDITION_FORM,
    verbose_name=_('Edition form for opportunity'),
    base_form_class=opp_forms.BaseCustomForm,
    extra_sub_cells=[opp_forms.OppTargetSubCell()],
    default=OpportunityEditionFormDefault,
)

del Opportunity
