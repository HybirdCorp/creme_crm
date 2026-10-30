################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2026  Hybird
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

from django.db import models

from creme.creme_core import models as core_models
from creme.creme_core.core.soft_reference import SoftReferenceCollector
from creme.reports import constants, get_report_model
from creme.reports.models import Field


class ReportRelationTypeRefCollector(SoftReferenceCollector):
    """Collect the Reports which reference a RelationType through their fields."""
    id = 'reports-report-rtype'
    model = core_models.RelationType

    def collect(self, instance):
        assert isinstance(instance, self.model)

        # NB: this simpler query is currently enough; we use a more future-proof one.
        #   >> yield from get_report_model().objects.filter( fields__name=instance.id)
        yield from get_report_model().objects.filter(models.Exists(
            Field.objects.filter(
                report=models.OuterRef('pk'),
                type=constants.RFT_RELATION,
                name=instance.id,
            ),
        ))


class ReportCustomFieldTypeRefCollector(SoftReferenceCollector):
    """Collect the Reports which reference a CustomField through their fields."""
    id = 'reports-report-cfield'
    model = core_models.CustomField

    def collect(self, instance):
        assert isinstance(instance, self.model)

        # NB: this simpler query is currently enough; we use a more future-proof one.
        #   >> yield from get_report_model().objects.filter( fields__name=instance.id)
        # yield from get_report_model().objects.filter(
        #     fields__name__startswith=instance.uuid,
        # ).distinct()
        yield from get_report_model().objects.filter(models.Exists(
            Field.objects.filter(
                report=models.OuterRef('pk'),
            ).filter(
                models.Q(type=constants.RFT_CUSTOM, name=instance.uuid)
                | models.Q(type=constants.RFT_AGG_CUSTOM, name__startswith=instance.uuid)
            ),
        ))
