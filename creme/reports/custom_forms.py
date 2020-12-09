# -*- coding: utf-8 -*-

from django.utils.translation import gettext_lazy as _

from creme import reports
from creme.creme_core.gui.custom_form import CustomFormDescriptor

from .forms import report as r_froms

Report = reports.get_report_model()

REPORT_CREATION_CFORM = CustomFormDescriptor(
    id='reports-report_creation',
    model=Report,
    verbose_name=_('Creation form for report (step 1)'),
    excluded_fields=('ct', 'filter'),
    extra_sub_cells=[r_froms.FilteredCTypeSubCell(model=Report)],
)
REPORT_EDITION_CFORM = CustomFormDescriptor(
    id='reports-report_edition',
    model=Report,
    form_type=CustomFormDescriptor.EDITION_FORM,
    verbose_name=_('Edition form for report'),
    excluded_fields=('ct', 'filter'),
    extra_sub_cells=[r_froms.FilterSubCell(model=Report)]
)

del Report
