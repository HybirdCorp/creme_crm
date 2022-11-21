from django.utils.translation import gettext_lazy as _

from creme import reports
from creme.creme_core.gui.custom_form import (
    CustomFormDefault,
    CustomFormDescriptor,
)

from .forms import report as report_forms

Report = reports.get_report_model()


class ReportCreationFormDescriptor(CustomFormDefault):
    CTYPE_N_FILTER = 'CTYPE_N_FILTER'
    sub_cells = {
        CTYPE_N_FILTER: report_forms.FilteredCTypeSubCell,
    }
    main_fields = ['user', 'name', CTYPE_N_FILTER]


class ReportEditionFormDefault(CustomFormDefault):
    FILTER = 'FILTER'
    sub_cells = {
        FILTER: report_forms.FilterSubCell,
    }
    main_fields = ['user', 'name', FILTER]


REPORT_CREATION_CFORM = CustomFormDescriptor(
    id='reports-report_creation',
    model=Report,
    verbose_name=_('Creation form for report (step 1)'),
    excluded_fields=('ct', 'filter'),
    extra_sub_cells=[report_forms.FilteredCTypeSubCell(model=Report)],
    default=ReportCreationFormDescriptor,
)
REPORT_EDITION_CFORM = CustomFormDescriptor(
    id='reports-report_edition',
    model=Report,
    form_type=CustomFormDescriptor.EDITION_FORM,
    verbose_name=_('Edition form for report'),
    excluded_fields=('ct', 'filter'),
    extra_sub_cells=[report_forms.FilterSubCell(model=Report)],
    default=ReportEditionFormDefault,
)

del Report
