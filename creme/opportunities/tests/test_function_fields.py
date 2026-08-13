from functools import partial

from django.utils.formats import number_format
from django.utils.translation import gettext as _

from creme.creme_core.core.entity_cell import EntityCellFunctionField
from creme.creme_core.core.function_field import function_field_registry
from creme.creme_core.core.sorter import AnnotationSortingItem
from creme.creme_core.gui.view_tag import ViewTag
from creme.creme_core.models import FieldsConfig
from creme.persons.tests.base import skipIfCustomOrganisation

from ..function_fields import TurnoverField, TurnoverSorter
from ..models import SalesPhase
from .base import (
    OpportunitiesBaseTestCase,
    Opportunity,
    skipIfCustomOpportunity,
)


@skipIfCustomOpportunity
@skipIfCustomOrganisation
class TurnoverFieldTestCase(OpportunitiesBaseTestCase):
    def test_get_weighted_sales__empty(self):
        user = self.login_as_root_and_get()

        target, emitter = self._create_target_n_emitter(user=user)
        create_opp = partial(
            Opportunity.objects.create,
            user=user,
            emitter=emitter, target=target,
            sales_phase=SalesPhase.objects.all()[0],
        )

        funf = function_field_registry.get(Opportunity, 'get_weighted_sales')
        self.assertIsInstance(funf, TurnoverField)

        # Empty ---
        opp_empty = create_opp(name='Opp (void)')
        self.assertIsNone(opp_empty.estimated_sales)
        self.assertIsNone(opp_empty.chance_to_win)
        zero = number_format('0.0')
        self.assertEqual(zero, funf(opp_empty, user).render(ViewTag.HTML_LIST))

        opp_filled = create_opp(name='Opp (ok)', estimated_sales=1000, chance_to_win=10)
        self.assertEqual(
            number_format('100.0'),
            funf(opp_filled, user).render(ViewTag.HTML_LIST),
        )

        opp_no_sales = create_opp(name='Opp (no sales)', chance_to_win=50)
        self.assertEqual(zero, funf(opp_no_sales, user).render(ViewTag.TEXT_PLAIN))

        opp_no_chance = create_opp(name='Opp (no chance)', estimated_sales=2000)
        self.assertEqual(zero, funf(opp_no_chance, user).render(ViewTag.TEXT_PLAIN))

        # Sorting ---
        sorter_class = funf.sorter_class
        self.assertEqual(TurnoverSorter, sorter_class)

        sorting_item = sorter_class().get_sorting_item(
            cell=EntityCellFunctionField(model=Opportunity, func_field=funf),
        )
        self.assertIsInstance(sorting_item, AnnotationSortingItem)
        self.assertEqual('opportunities-weighted_sales', sorting_item.name)

        qs = Opportunity.objects.filter(
            id__in=[o.id for o in (opp_empty, opp_no_sales, opp_no_chance, opp_filled)],
        ).annotate(ann_sales=sorting_item.db_expression)

        annotated_opps = [*qs]
        self.assertListEqual(
            [o.name for o in (opp_no_chance, opp_no_sales, opp_filled, opp_empty)],
            [o.name for o in annotated_opps],
        )
        self.assertEqual(0, annotated_opps[0].ann_sales)
        self.assertEqual(0, annotated_opps[1].ann_sales)
        self.assertEqual(10000, annotated_opps[2].ann_sales)
        self.assertEqual(0, annotated_opps[3].ann_sales)

        self.assertListEqual(
            [o.name for o in (opp_empty, opp_no_sales, opp_no_chance, opp_filled)],
            [o.name for o in qs.order_by('ann_sales', 'id')],
        )

    def test_hidden_field__estimated_sales(self):
        """With field 'estimated_sales' hidden with FieldsConfig."""
        user = self.login_as_root_and_get()

        FieldsConfig.objects.create(
            content_type=Opportunity,
            descriptions=[('estimated_sales', {FieldsConfig.HIDDEN: True})],
        )

        opportunity = self._create_opportunity_n_organisations(user=user)[0]

        FieldsConfig.objects.get_for_model(Opportunity)

        funf = function_field_registry.get(Opportunity, 'get_weighted_sales')

        with self.assertNumQueries(0):
            w_sales = funf(opportunity, user).render(ViewTag.TEXT_PLAIN)

        self.assertEqual(_('Error: «Estimated sales» is hidden'), w_sales)

        # Sorting ---
        self.assertIsNone(funf.sorter_class().get_sorting_item(
            cell=EntityCellFunctionField(model=Opportunity, func_field=funf),
        ))

    def test_hidden_field__chance_to_win(self):
        """With field 'chance_to_win' hidden with FieldsConfig."""
        user = self.login_as_root_and_get()

        FieldsConfig.objects.create(
            content_type=Opportunity,
            descriptions=[('chance_to_win', {FieldsConfig.HIDDEN: True})],
        )

        opportunity = self._create_opportunity_n_organisations(user=user)[0]

        FieldsConfig.objects.get_for_model(Opportunity)

        funf = function_field_registry.get(Opportunity, 'get_weighted_sales')

        with self.assertNumQueries(0):
            w_sales = funf(opportunity, user).render(ViewTag.TEXT_PLAIN)

        self.assertEqual(_(r'Error: «% of chance to win» is hidden'), w_sales)

        # Sorting ---
        self.assertIsNone(funf.sorter_class().get_sorting_item(
            cell=EntityCellFunctionField(model=Opportunity, func_field=funf),
        ))
