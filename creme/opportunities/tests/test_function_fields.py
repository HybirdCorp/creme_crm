from django.utils.formats import number_format
from django.utils.translation import gettext as _

from creme.creme_core.core.function_field import function_field_registry
from creme.creme_core.gui.view_tag import ViewTag
from creme.creme_core.models import FieldsConfig
from creme.persons.tests.base import skipIfCustomOrganisation

from .base import (
    OpportunitiesBaseTestCase,
    Opportunity,
    skipIfCustomOpportunity,
)


@skipIfCustomOpportunity
class TurnoverFieldTestCase(OpportunitiesBaseTestCase):
    @skipIfCustomOrganisation
    def test_get_weighted_sales(self):
        user = self.login_as_root_and_get()

        opportunity = self._create_opportunity_n_organisations(user=user)[0]
        funf = function_field_registry.get(Opportunity, 'get_weighted_sales')
        self.assertIsNotNone(funf)

        self.assertIsNone(opportunity.estimated_sales)
        self.assertIsNone(opportunity.chance_to_win)
        self.assertEqual(number_format('0.0'), funf(opportunity, user).render(ViewTag.HTML_LIST))

        opportunity.estimated_sales = 1000
        opportunity.chance_to_win   = 10
        self.assertEqual(
            number_format('100.0'),
            funf(opportunity, user).render(ViewTag.HTML_LIST),
        )

    @skipIfCustomOrganisation
    def test_get_weighted_sales__hidden(self):
        "With field 'estimated_sales' hidden with FieldsConfig."
        user = self.login_as_root_and_get()

        FieldsConfig.objects.create(
            content_type=Opportunity,
            descriptions=[('estimated_sales', {FieldsConfig.HIDDEN: True})],
        )

        opportunity = self._create_opportunity_n_organisations(user=user)[0]

        FieldsConfig.objects.get_for_model(Opportunity)

        funf = function_field_registry.get(Opportunity, 'get_weighted_sales')

        with self.assertNumQueries(0):
            w_sales = funf(opportunity, user).render(ViewTag.HTML_LIST)

        self.assertEqual(_('Error: «Estimated sales» is hidden'), w_sales)
