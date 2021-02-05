# -*- coding: utf-8 -*-

from django.utils.translation import gettext as _
from django.utils.translation import pgettext

from creme.creme_core.models import (
    FakeContact,
    FakeImage,
    FakeOrganisation,
    FieldsConfig,
    InstanceBrickConfigItem,
)
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.tests.fake_constants import (
    FAKE_REL_SUB_BILL_ISSUED,
    FAKE_REL_SUB_EMPLOYED_BY,
)
from creme.reports.bricks import ReportGraphBrick
# from creme.reports.constants import (
#     RGA_COUNT,
#     RGF_FK,
#     RGF_NOLINK,
#     RGF_RELATION,
#     RGT_YEAR,
# )
from creme.reports.constants import (
    RGF_FK,
    RGF_NOLINK,
    RGF_RELATION,
    AbscissaGroup,
    OrdinateAggregator,
)
# from creme.reports.constants import AbscissaGroup
from creme.reports.core.graph.fetcher import (
    RegularFieldLinkedGraphFetcher,
    RelationLinkedGraphFetcher,
    SimpleGraphFetcher,
)
from creme.reports.tests.base import Report, ReportGraph


# TODO: test fetch() ??
class GraphFetcherTestCase(CremeTestCase):
    def test_simple(self):
        user = self.create_user()
        report = Report.objects.create(user=user, name='Field Test', ct=FakeContact)
        graph = ReportGraph.objects.create(
            user=user, name='Field Test', linked_report=report,
            # abscissa_cell_value='created', abscissa_type=RGT_YEAR,
            abscissa_cell_value='created', abscissa_type=AbscissaGroup.YEAR,
            # ordinate_type=RGA_COUNT,
            ordinate_type=OrdinateAggregator.COUNT,
        )

        fetcher1 = SimpleGraphFetcher(graph=graph)
        self.assertIsNone(fetcher1.error)
        self.assertEqual(_('No volatile column'), fetcher1.verbose_name)

        ibci = fetcher1.create_brick_config_item()
        self.assertIsInstance(ibci, InstanceBrickConfigItem)
        self.assertEqual(graph.id, ibci.entity_id)
        self.assertEqual(ReportGraphBrick.id_, ibci.brick_class_id)
        self.assertEqual(RGF_NOLINK, ibci.get_extra_data('type'))
        self.assertIsNone(ibci.get_extra_data('value'))

        # ---
        fetcher2 = SimpleGraphFetcher(graph=graph, value='last_name')
        self.assertEqual(
            _('No value is needed.'),
            fetcher2.error
        )

        self.assertListEqual(
            [('', pgettext('reports-volatile_choice', 'None'))],
            [*SimpleGraphFetcher.choices(FakeContact)]
        )

        # ----
        # TODO: move to test for bricks ?
        brick = ReportGraphBrick(ibci)
        self.assertIsNone(brick.errors)
        self.assertEqual(
            '{} - {}'.format(graph.name, _('No volatile column')),
            brick.verbose_name
        )
        self.assertListEqual([], brick.target_ctypes)

        b_fetcher = brick.fetcher
        self.assertIsInstance(b_fetcher, SimpleGraphFetcher)
        self.assertIsNone(b_fetcher.error)
        self.assertEqual(graph, b_fetcher.graph)

    def test_fk01(self):
        user = self.create_user()
        report = Report.objects.create(user=user, name='Field Test', ct=FakeContact)
        graph = ReportGraph.objects.create(
            user=user, name='Field Test', linked_report=report,
            # abscissa_cell_value='created', abscissa_type=RGT_YEAR,
            abscissa_cell_value='created', abscissa_type=AbscissaGroup.YEAR,
            # ordinate_type=RGA_COUNT,
            ordinate_type=OrdinateAggregator.COUNT,
        )

        fname = 'image'
        fetcher1 = RegularFieldLinkedGraphFetcher(graph=graph, value=fname)
        self.assertIsNone(fetcher1.error)
        self.assertEqual(
            _('{field} (Field)').format(field=_('Photograph')),
            fetcher1.verbose_name
        )

        ibci = fetcher1.create_brick_config_item()
        self.assertEqual(RGF_FK, ibci.get_extra_data('type'))
        self.assertEqual(fname, ibci.get_extra_data('value'))

        fetcher2 = RegularFieldLinkedGraphFetcher(graph=graph)
        self.assertEqual(
            _('No field given.'),
            fetcher2.error
        )
        self.assertEqual('??', fetcher2.verbose_name)

        fetcher3 = RegularFieldLinkedGraphFetcher(graph=graph, value='invalid')
        self.assertEqual(
            _('The field is invalid.'),
            fetcher3.error
        )

        fetcher4 = RegularFieldLinkedGraphFetcher(graph=graph, value='last_name')
        self.assertEqual(
            _('The field is invalid (not a foreign key).'),
            fetcher4.error
        )

        fetcher5 = RegularFieldLinkedGraphFetcher(graph=graph, value='position')
        self.assertEqual(
            _('The field is invalid (not a foreign key to CremeEntity).'),
            fetcher5.error
        )

        self.assertListEqual(
            [('image', _('Photograph'))],
            [*RegularFieldLinkedGraphFetcher.choices(FakeContact)]
        )

        # ----
        # TODO: move to test for bricks ?
        brick = ReportGraphBrick(ibci)
        self.assertIsNone(brick.errors)
        self.assertEqual(
            '{} - {}'.format(
                graph.name,
                _('{field} (Field)').format(field=_('Photograph')),
            ),
            brick.verbose_name
        )
        self.assertListEqual([FakeImage], brick.target_ctypes)

        b_fetcher = brick.fetcher
        self.assertIsInstance(b_fetcher, RegularFieldLinkedGraphFetcher)
        self.assertIsNone(b_fetcher.error)
        self.assertEqual(fname, b_fetcher._field.name)

    def test_fk02(self):
        "Hidden field."
        hidden_fname = 'image'
        FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[(hidden_fname, {FieldsConfig.HIDDEN: True})],
        )

        user = self.create_user()
        report = Report.objects.create(user=user, name='Field Test', ct=FakeContact)
        graph = ReportGraph(user=user, name='Field Test', linked_report=report)

        fetcher = RegularFieldLinkedGraphFetcher(graph=graph, value=hidden_fname)
        self.assertEqual(
            _('The field is hidden.'),
            fetcher.error
        )

    def test_relation(self):
        user = self.create_user()
        report = Report.objects.create(user=user, name='Field Test', ct=FakeContact)
        graph = ReportGraph.objects.create(
            user=user, name='Field Test', linked_report=report,
            # abscissa_cell_value='created', abscissa_type=RGT_YEAR,
            abscissa_cell_value='created', abscissa_type=AbscissaGroup.YEAR,
            # ordinate_type=RGA_COUNT,
            ordinate_type=OrdinateAggregator.COUNT,
        )

        fetcher1 = RelationLinkedGraphFetcher(graph=graph, value=FAKE_REL_SUB_EMPLOYED_BY)
        self.assertIsNone(fetcher1.error)
        self.assertEqual(
            _('{rtype} (Relationship)').format(
                rtype='is an employee of — employs',
            ),
            fetcher1.verbose_name
        )

        ibci = fetcher1.create_brick_config_item()
        self.assertEqual(RGF_RELATION, ibci.get_extra_data('type'))
        self.assertEqual(FAKE_REL_SUB_EMPLOYED_BY, ibci.get_extra_data('value'))

        fetcher2 = RelationLinkedGraphFetcher(graph=graph)
        self.assertEqual(
            _('No relationship type given.'),
            fetcher2.error
        )
        self.assertEqual('??', fetcher2.verbose_name)

        fetcher3 = RelationLinkedGraphFetcher(graph=graph, value='invalid')
        self.assertEqual(
            _('The relationship type is invalid.'),
            fetcher3.error
        )

        fetcher4 = RelationLinkedGraphFetcher(graph=graph, value=FAKE_REL_SUB_BILL_ISSUED)
        self.assertEqual(
            _('The relationship type is not compatible with «{}».').format(
                'Test Contact',
            ),
            fetcher4.error
        )

        choices = [*RelationLinkedGraphFetcher.choices(FakeContact)]
        self.assertInChoices(
            value=f'{FAKE_REL_SUB_EMPLOYED_BY}',
            label='is an employee of — employs',
            choices=choices,
        )
        self.assertNotInChoices(
            value=f'{FAKE_REL_SUB_BILL_ISSUED}',
            choices=choices,
        )

        # ----
        # TODO: move to test for bricks ?
        brick = ReportGraphBrick(ibci)
        self.assertIsNone(brick.errors)
        self.assertListEqual([FakeOrganisation], brick.target_ctypes)

    def test_create_brick_config_item(self):
        "Other brick class."
        class OtherReportGraphBrick(ReportGraphBrick):
            id_ = ReportGraphBrick.generate_id('reports', 'other_graph')

        user = self.create_user()
        report = Report.objects.create(user=user, name='Field Test', ct=FakeContact)
        graph = ReportGraph.objects.create(
            user=user, name='Field Test', linked_report=report,
            # abscissa_cell_value='created', abscissa_type=RGT_YEAR,
            abscissa_cell_value='created', abscissa_type=AbscissaGroup.YEAR,
            # ordinate_type=RGA_COUNT,
            ordinate_type=OrdinateAggregator.COUNT,
        )

        ibci = SimpleGraphFetcher(graph=graph).create_brick_config_item(
            brick_class=OtherReportGraphBrick,
        )
        self.assertEqual(OtherReportGraphBrick.id_, ibci.brick_class_id)
