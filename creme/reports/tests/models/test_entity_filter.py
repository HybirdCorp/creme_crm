from django.utils.translation import gettext as _

from creme.creme_core.models import EntityFilter
from creme.creme_core.tests.fake_models import FakeContact
from creme.reports.constants import EF_REPORTS
from creme.reports.tests.base import BaseReportsTestCase


class EntityFilterTestCase(BaseReportsTestCase):
    def test_str(self):
        efilter = EntityFilter(
            name='Filter for reports',
            entity_type=FakeContact,
            filter_type=EF_REPORTS,
        )
        self.assertEqual(f'{efilter.name} [{_("Report")}]', str(efilter))
