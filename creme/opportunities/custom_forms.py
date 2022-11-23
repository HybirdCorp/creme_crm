from django.utils.translation import gettext_lazy as _

import creme.opportunities.forms.opportunity as opp_forms
from creme import opportunities
from creme.creme_core.gui.custom_form import CustomFormDescriptor

Opportunity = opportunities.get_opportunity_model()

OPPORTUNITY_CREATION_CFORM = CustomFormDescriptor(
    id='opportunities-opportunity_creation',
    model=Opportunity,
    verbose_name=_('Creation form for opportunity'),
    base_form_class=opp_forms.BaseCustomForm,
    extra_sub_cells=[
        opp_forms.OppEmitterSubCell(),
        opp_forms.OppTargetSubCell(),
    ],
)
OPPORTUNITY_EDITION_CFORM = CustomFormDescriptor(
    id='opportunities-opportunity_edition',
    model=Opportunity,
    form_type=CustomFormDescriptor.EDITION_FORM,
    verbose_name=_('Edition form for opportunity'),
    base_form_class=opp_forms.BaseCustomForm,
    extra_sub_cells=[opp_forms.OppTargetSubCell()],
)

del Opportunity
