################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2022-2025  Hybird
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

from collections.abc import Sequence
from random import randint

from creme.creme_core.gui.bricks import Brick


class ChartBrick(Brick):
    """
    Base class for bricks containing D3js charts.
    """
    template_name = "sketch/bricks/chart.html"

    def get_chart_props(self, context):
        """
        Properties to set colors, fonts, sizes or animations of a chart
        """
        return {}

    def get_chart_data(self, context):
        """
        Raw data for the chart. Must be implemented !
        """
        raise NotImplementedError

    def _render_chart(self, context):
        return self._render(
            self.get_template_context(
                context,
                data=self.get_chart_data(context),
                props=self.get_chart_props(context)
            )
        )


class BarChartBrick(ChartBrick):
    """
    Base brick that draws BarChart.
    Expects a list of dict with x (sequential) & y (numeric) :
    ```
        [{x: "A", y: 12.5}, ...]
    ```
    """
    template_name = "sketch/bricks/bar-chart.html"

    # Show limits along the Y axis : list of values drawn as horizontal lines
    limits: Sequence[float] = ()
    # Enable animations when the data are updated
    enable_transition = True
    # Title of the horizontal axis
    abscissa_title: str = ''
    # Title of the vertical axis
    ordinate_title: str = ''

    def get_chart_props(self, context):
        return {
            "limits": self.limits,
            "transition": self.enable_transition,
            "xAxisTitle": self.abscissa_title,
            "yAxisTitle": self.ordinate_title,
        }


class GroupBarChartBrick(ChartBrick):
    """
    Base brick that draws GroupBarChart.
    Expects a list of dict with x (sequential), y (numeric) & group (sequential)
    ```
        [{x: "A", y: 12.5, group: "G1"}, ...]
    ```
    The "group" property is the new X axis and the bars are grouped by this value :
    ```
    [
        {x: 0, y: 1, group: 'A'}, {x: 1, y: 5, group: 'A'}, {x: 2, y: 2, group: 'A'},
        {x: 0, y: 3, group: 'B'}, {x: 1, y: 4, group: 'B'}
    ]
    ```
    ↑ Y
      |      |
      |      |              |
      |      |           |  |
      |      |  |        |  |
      |   |  |  |        |  |
      +-------------------------------
            'A'          'B'     group →
    """
    template_name = "sketch/bricks/groupbar-chart.html"

    # Show limits along the Y axis : list of values drawn as horizontal lines
    limits: Sequence[float] = ()
    # Enable animations when the data are updated
    enable_transition = True
    # Toggle legend (horizontal)
    enable_legend = True

    def get_chart_props(self, context):
        return {
            "limits": self.limits,
            "transition": self.enable_transition,
            "showLegend": self.enable_legend,
        }


class StackBarChartBrick(ChartBrick):
    """
    Base brick that draws StackBarChart.
    Expects a list of dict with x (sequential), y (numeric) & group (sequential)
    ```
        [{x: "A", y: 12.5, group: "G1"}, ...]
    ```
    The "group" property is the new X axis and the bars are stacked by this value :
    ```
    [
        {x: 0, y: 1, group: 'A'}, {x: 1, y: 5, group: 'A'}, {x: 2, y: 2, group: 'A'},
        {x: 0, y: 3, group: 'B'}, {x: 1, y: 4, group: 'B'}
    ]
    ```
    ↑ Y
      |   +
      |   +      *
      |   *      *
      |   *      *
      |   *      *
      |   *      |
      |   *      |
      |   |      |
      +--------------------
         'A'    'B'   group →
    """
    template_name = "sketch/bricks/stackbar-chart.html"

    # Show limits along the Y axis : list of values drawn as horizontal lines
    limits: Sequence[float] = ()
    # Enable animations when the data are updated
    enable_transition = True
    # Toggle legend (horizontal)
    enable_legend = True

    def get_chart_props(self, context):
        return {
            "limits": self.limits,
            "transition": self.enable_transition,
            "showLegend": self.enable_legend,
        }


class DonutChartBrick(ChartBrick):
    """
    Base brick that draws DonutChart.
    Expects a list of dict with x (sequential) & y (numeric) :
    ```
        [{x: "A", y: 12.5}, ...]
    ```
    The X value is displayed in the legend (if shown) and Y in the slices.
    """
    template_name = "sketch/bricks/donut-chart.html"

    # Enable animations when the data are updated
    enable_transition = True
    # Donut stroke size
    band_size = 60
    # List of colors slices. Will loop on this list to find the next slice color
    color_range = None
    # Toggle legend (vertical)
    enable_legend = True

    def get_chart_props(self, context):
        props = {
            "band": self.band_size,
            "transition": self.enable_transition,
        }

        if self.color_range:
            props['colors'] = self.color_range

        return props


class LineChartBrick(ChartBrick):
    """
    Base brick that draws LineChart.
    Expects a list of dict with x (sequential) & y (numeric) :
    ```
        [{x: "A", y: 12.5}, ...]
    ```
    The X value is displayed in the legend (if shown) and Y in the slices.
    """
    template_name = "sketch/bricks/line-chart.html"

    # Show limits along the Y axis : list of values drawn as horizontal lines
    limits: Sequence[float] = ()
    # Enable animations when the data are updated
    enable_transition = True
    # Title of the horizontal axis
    abscissa_title: str = ''
    # Title of the vertical axis
    ordinate_title: str = ''

    enable_tooltip = True

    def get_chart_props(self, context):
        return {
            "limits": self.limits,
            "transition": self.enable_transition,
            "xAxisTitle": self.abscissa_title,
            "yAxisTitle": self.ordinate_title,
            "showTooltip": self.enable_tooltip,
        }


class DemoGroupBarChartBrick(GroupBarChartBrick):
    """
    Brick that draws a GroupBarChart from random data. Can be used as demo.
    """
    id = GroupBarChartBrick.generate_id('sketch', 'demo_groupbar_chart')
    verbose_name = "Demo Grouped Bar Chart"

    def get_chart_data(self, context):
        data = []
        groups = ["Won", "Lost", "In Progress", "Canceled", "To Do"]

        for group in groups[:randint(2, 5)]:
            items = [{
                "x": f"A {i}",
                "y": randint(1, 100),
                "group": group,
            } for i in range(3, 8)]

            data.extend(items)

        return data

    def detailview_display(self, context):
        return self._render_chart(context)

    def home_display(self, context):
        return self._render_chart(context)


class DemoStackBarChartBrick(StackBarChartBrick):
    """
    Brick that draws a StackBarChart from random data. Can be used as demo.
    """
    id = StackBarChartBrick.generate_id('sketch', 'demo_stackbar_chart')
    verbose_name = "Demo Stacked Bar Chart"

    def get_chart_data(self, context):
        data = []
        groups = ["Won", "Lost", "In Progress", "Canceled", "To Do"]

        for group in groups[:randint(2, 5)]:
            items = [{
                "x": f"A {i}",
                "y": randint(1, 100),
                "group": group,
            } for i in range(3, 8)]

            data.extend(items)

        return data

    def detailview_display(self, context):
        return self._render_chart(context)

    def home_display(self, context):
        return self._render_chart(context)


class DemoBarChartBrick(BarChartBrick):
    """
    Brick that draws a BarChart from random data. Can be used as demo.
    """
    id = BarChartBrick.generate_id('sketch', 'demo_bar_chart')
    verbose_name = "Demo Bar Chart"
    abscissa_title = "Axis of Abscissas"
    ordinate_title = "Axis of Ordinates"

    def get_chart_data(self, context):
        return [{"x": f"A {i}", "y": randint(1, 1500)} for i in range(1, randint(5, 40))]

    def detailview_display(self, context):
        return self._render_chart(context)

    def home_display(self, context):
        return self._render_chart(context)


class DemoDonutChartBrick(DonutChartBrick):
    """
    Brick that draws a DonutChart from random data. Can be used as demo.
    """
    id = DonutChartBrick.generate_id('sketch', 'demo_donut_chart')
    verbose_name = "Demo Donut Chart"

    def get_chart_data(self, context):
        return [{"x": f"A {i}", "y": randint(1, 100)} for i in range(1, randint(5, 10))]

    def detailview_display(self, context):
        return self._render_chart(context)

    def home_display(self, context):
        return self._render_chart(context)


class DemoLineChartBrick(LineChartBrick):
    """
    Brick that draws a LineChart from random data. Can be used as demo.
    """
    id = DonutChartBrick.generate_id('sketch', 'demo_line_chart')
    verbose_name = "Demo Line Chart"
    abscissa_title = "Axis of Abscissas"
    ordinate_title = "Axis of Ordinates"

    def get_chart_data(self, context):
        return [{"x": f"Line Dot {i}", "y": randint(1, 1500)} for i in range(1, randint(5, 40))]

    def detailview_display(self, context):
        return self._render_chart(context)

    def home_display(self, context):
        return self._render_chart(context)
