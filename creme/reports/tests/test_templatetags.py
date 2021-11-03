# -*- coding: utf-8 -*-

import json

from django.template import Context, Template
from django.utils.translation import gettext as _

from creme.creme_core.models import FakeOrganisation
from creme.reports.report_chart_registry import (
    ReportChart,
    ReportChartRegistry,
)

from .base import BaseReportsTestCase, Report, ReportGraph


class ReportsTagsTestCase(BaseReportsTestCase):
    def test_chart_json(self):
        rgraph = ReportGraph(
            linked_report=Report(name='Organisation report', ct=FakeOrganisation),
            name='Number of created organisations / year',
            abscissa_cell_value='created',
            abscissa_type=ReportGraph.Group.YEAR,
            ordinate_type=ReportGraph.Aggregator.COUNT,
        )

        ctxt = Context({
            'graph': rgraph,
            'chart': ReportChart('barchart', 'Histogram'),
        })

        with self.assertNoException():
            render1 = Template(
                r'{% load reports_tags %}'
                r'{% reports_chart_json graph chart %}'
            ).render(ctxt)

        with self.assertNoException():
            data1 = json.loads(render1)

        self.assertIsInstance(data1, dict)
        self.assertDictEqual(
            {
                'text': f'<b>{rgraph.name}</b>',
                'textColor': 'black',
                'fontSize': '13pt',
                'renderer': 'jqplot.DivTitleRenderer',
            },
            data1.get('title'),
        )

        # ---
        with self.assertNoException():
            render2 = Template(
                r'{% load reports_tags %}'
                r'{% reports_chart_json graph chart is_small=True %}'
            ).render(ctxt)

        with self.assertNoException():
            data2 = json.loads(render2)

        self.assertDictEqual(
            {
                'text': f'<b>{rgraph.name}</b>',
                'textColor': 'black',
                'fontSize': '12pt',
                'renderer': 'jqplot.DivTitleRenderer',
            },
            data2.get('title'),
        )

    def test_chart_selector(self):
        chart1 = ReportChart('barchart', 'Histogram')
        chart2 = ReportChart('piechart', 'Pie')
        charts = ReportChartRegistry().register(chart1).register(chart2)

        rgraph = ReportGraph(
            linked_report=Report(name='Organisation report', ct=FakeOrganisation),
            name='Number of created organisations / year',
            abscissa_cell_value='created',
            abscissa_type=ReportGraph.Group.YEAR,
            ordinate_type=ReportGraph.Aggregator.COUNT,
            chart=chart1.name,
        )

        with self.assertNoException():
            render = Template(
                r'{% load reports_tags %}'
                r'<ul>{% reports_chart_selector graph %}</ul>'
            ).render(Context({
                'graph': rgraph,
                'report_charts': charts,
            }))

        tree = self.get_html_tree(render)

        chart_select_node = self.get_html_node_or_fail(
            self.get_html_node_or_fail(tree, './/li[@chained-name="graph"]'),
            './/select',
        )
        self.assertCountEqual(
            [
                (chart1.name, chart1.label, True),
                (chart2.name, chart2.label, False),
            ],
            [
                (n.attrib.get('value'), n.text, 'selected' in n.attrib)
                for n in chart_select_node.findall('.//option')
            ],
        )

        sort_select_node = self.get_html_node_or_fail(
            self.get_html_node_or_fail(tree, './/li[@chained-name="sort"]'),
            './/select',
        )
        self.assertCountEqual(
            [
                ('ASC',  _('Ascending'), True),
                ('DESC', _('Descending'), False),
            ],
            [
                (n.attrib.get('value'), n.text, 'selected' in n.attrib)
                for n in sort_select_node.findall('.//option')
            ],
        )

    def test_chart_labels(self):
        chart1 = ReportChart('barchart', 'Histogram')
        chart2 = ReportChart('piechart', 'Pie')
        charts = ReportChartRegistry().register(chart1).register(chart2)

        with self.assertNoException():
            render = Template(
                r'{% load reports_tags %}'
                r'{% with labels=charts|reports_chart_labels %}'
                r'<select>'
                r'{% for name, label in labels.items %}'
                r'  <option value="{{name}}">{{label}}</option>'
                r'{% endfor %}'
                r'</select>'
                r'{% endwith %}'
            ).render(Context({
                'charts': charts,
            }))

        tree = self.get_html_tree(render)
        select_node = self.get_html_node_or_fail(tree, './/select')
        self.assertCountEqual(
            [
                (chart1.name, chart1.label),
                (chart2.name, chart2.label),
            ],
            [
                (n.attrib.get('value'), n.text)
                for n in select_node.findall('.//option')
            ],
        )

    def test_graph_ordinate(self):
        report = Report(name='Organisation report', ct=FakeOrganisation)
        rgraph = ReportGraph(
            linked_report=report,
            name='Number of created organisations / year',
            abscissa_cell_value='created',
            abscissa_type=ReportGraph.Group.YEAR,
            ordinate_type=ReportGraph.Aggregator.COUNT,
        )

        with self.assertNoException():
            template = Template(
                r'{% load reports_tags %}'
                r'{% reports_graph_ordinate graph %}'
            )

        with self.assertNoException():
            render1 = template.render(Context({'graph': rgraph}))

        self.assertEqual(_('Count'), render1.strip())

        # ---
        rgraph = ReportGraph(
            linked_report=report,
            name='Max capital / year',
            abscissa_cell_value='created',
            abscissa_type=ReportGraph.Group.YEAR,
            ordinate_type=ReportGraph.Aggregator.MAX,
            ordinate_cell_key='regular_field-capital',
        )

        with self.assertNoException():
            render2 = template.render(Context({'graph': rgraph}))

        self.assertEqual(
            # _('Count'),
            f"{_('Capital')} - {_('Maximum')}",
            render2.strip(),
        )
