from django.urls.base import reverse
from parameterized import parameterized

from creme.creme_core.gui.bricks import brick_registry
from creme.creme_core.models import FakeContact
from creme.creme_core.templatetags.creme_core_tags import jsondata
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.sketch import bricks


class ChartBrickTestCase(BrickTestCaseMixin, CremeTestCase):
    def render_brick(self, user, brick_class):
        entity = FakeContact.objects.create(user=user, first_name='Any', last_name='Entity')

        brick_registry.register(brick_class)

        response = self.assertGET200(
            reverse('creme_core__reload_detailview_bricks', args=(entity.id,)),
            data={'brick_id': brick_class.id},
        )

        return response.json()[0][1]

    @parameterized.expand([
        [
            bricks.BarChartBrick,
            {'limits': (), 'transition': True, 'xAxisTitle': '', 'yAxisTitle': ''},
        ],
        [
            bricks.LineChartBrick,
            {
                'limits': (),
                'transition': True,
                'xAxisTitle': '',
                'yAxisTitle': '',
                'showTooltip': True,
            },
        ],
        [bricks.DonutChartBrick, {'band': 60, 'transition': True}],
        [bricks.GroupBarChartBrick, {'limits': (), 'transition': True, 'showLegend': True}],
        [bricks.StackBarChartBrick, {'limits': (), 'transition': True, 'showLegend': True}],
    ])
    def test_chart_default_props(self, chart_class, expected):
        class FooChartBrick(chart_class):
            id_ = bricks.Brick.generate_id('sketch', str(chart_class))

            def get_chart_data(self, context):
                return []

        brick = FooChartBrick()

        self.assertEqual(expected, brick.get_chart_props({}))

    @parameterized.expand([
        [
            bricks.DemoBarChartBrick,
            {
                'limits': (),
                'transition': True,
                'xAxisTitle': "Axis of Abscissas",
                'yAxisTitle': "Axis of Ordinates",
            },
        ],
        [
            bricks.DemoLineChartBrick,
            {
                'limits': (),
                'transition': True,
                'xAxisTitle': "Axis of Abscissas",
                'yAxisTitle': "Axis of Ordinates",
                'showTooltip': True,
            },
        ],
        [bricks.DemoDonutChartBrick, {'band': 60, 'transition': True}],
        [
            bricks.DemoGroupBarChartBrick,
            {'limits': (), 'transition': True, 'showLegend': True},
        ],
        [
            bricks.DemoStackBarChartBrick,
            {'limits': (), 'transition': True, 'showLegend': True},
        ],
    ])
    def test_demo_chart_render(self, chart_class, expected):
        user = self.login_as_root_and_get()
        content = self.render_brick(user, chart_class)

        self.assertInHTML(
            jsondata(expected, **{'class': 'sketch-chart-props'}), content, 1,
        )
