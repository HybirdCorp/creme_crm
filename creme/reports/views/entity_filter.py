################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2024  Hybird
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
################################################################################

from django.urls import reverse
from django.utils.translation import gettext_lazy as _

import creme.creme_config.views.entity_filter as config_views
import creme.creme_core.views.entity_filter as core_views
import creme.reports.forms.entity_filter as efilter_forms
from creme.reports.constants import EF_REPORTS


class ReportEntityFilterDetail(core_views.EntityFilterDetail):
    template_name = 'reports/detail/entity-filter.html'
    permissions = 'reports'
    bricks_reload_url_name = 'reports__reload_efilter_bricks'
    efilter_type = EF_REPORTS


class ReportEntityFilterBricksReloading(core_views.EntityFilterBricksReloading):
    permissions = 'reports'
    filter_type = EF_REPORTS


class ReportEntityFilterCreation(config_views.EntityFilterCreation):
    form_class = efilter_forms.ReportsEntityFilterCreationForm
    title = _('Create a filter for «{model}» specific to Reports')
    permissions = 'reports'
    efilter_type = EF_REPORTS


class ReportEntityFilterEdition(core_views.EntityFilterEdition):
    permissions = 'reports'
    efilter_type = EF_REPORTS


class ReportEntityFilterEditionPopup(config_views.EntityFilterEdition):
    permissions = 'reports'
    efilter_type = EF_REPORTS


class ReportEntityFilterDeletion(core_views.EntityFilterDeletion):
    permissions = 'reports'
    efilter_type = EF_REPORTS

    def get_success_url(self):
        # TODO: callback_url?
        # TODO: if admin perms ?
        #    return reverse('creme_config__app_portal', args=('reports',))
        return reverse('reports__list_reports')
