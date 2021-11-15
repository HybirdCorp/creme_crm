# -*- coding: utf-8 -*-

from functools import partial
from json import loads

from django.template import Context, Template
from django.utils.html import escape
from django.utils.translation import gettext as _

from ..core import PollLineType
from ..models import PollFormLineCondition, PollFormSection, PollReplyLine
from ..utils import NodeStyle, SectionTree, StatsTree
from .base import (
    PollForm,
    PollReply,
    _PollsTestCase,
    skipIfCustomPollForm,
    skipIfCustomPollReply,
)


@skipIfCustomPollForm
class PollsTagsTestCase(_PollsTestCase):
    def test_line_condition(self):
        user = self.create_user()
        pform = PollForm.objects.create(user=user, name='Form#1')

        create_l = self._get_formline_creator(pform=pform)
        choices = [[1, 'A little bit'], [2, 'A bit'], [3, 'A lot']]

        lines = [
            create_l('How do you like swallows?', qtype=PollLineType.ENUM,       choices=choices),
            create_l('How do you like parrots?',  qtype=PollLineType.MULTI_ENUM, choices=choices),
            create_l('Do you love all birds?',    qtype=PollLineType.STRING),
        ]

        create_cond = partial(
            PollFormLineCondition.objects.create,
            line=lines[2],
            operator=PollFormLineCondition.EQUALS,
        )
        cond1 = create_cond(source=lines[0], raw_answer='1')
        cond2 = create_cond(source=lines[1], raw_answer='[2,3]')

        nodes = SectionTree(pform)

        with self.assertNoException():
            tplt = Template(
                r'{% load polls_tags %}'
                r'{% poll_line_condition nodes condition %}'
            )
            render1 = tplt.render(Context({'nodes': nodes, 'condition': cond1}))

        self.assertEqual(
            _('The answer to the question #{number} is «{answer}».').format(
                number=1, answer=choices[0][1],
            ),
            render1.strip(),
        )

        # ---
        with self.assertNoException():
            render2 = tplt.render(Context({'nodes': nodes, 'condition': cond2}))

        self.assertEqual(
            _('The answer to the question #{number} contains «{answer}».').format(
                number=2,
                answer=f'{choices[1][1]} / {choices[2][1]}',
            ),
            render2.strip(),
        )

    def test_node_number(self):
        user = self.create_user()
        pform = PollForm.objects.create(user=user, name='Form#1')

        create_l = self._get_formline_creator(pform=pform)
        qtype = PollLineType.STRING
        create_l('How do you like swallows?', qtype=qtype)
        create_l('How do you like parrots?',  qtype=qtype)
        create_l('Do you love all birds?',    qtype=qtype)

        with self.assertNoException():
            render = Template(
                r'{% load polls_tags %}'
                r'{% for node in nodes %}{% poll_node_number style node %}#{% endfor %}'
            ).render(Context({'nodes': SectionTree(pform), 'style': NodeStyle()}))

        self.assertEqual('1#2#3#', render.strip())

    def test_node_css(self):
        user = self.create_user()
        pform = PollForm.objects.create(user=user, name='Form#1')
        create_section = partial(PollFormSection.objects.create, pform=pform, order=1)
        create_l = self._get_formline_creator(pform=pform)

        section1   = create_section(name='Chapter I')
        section11  = create_section(name='Chapter I.1', parent=section1)
        section111 = create_section(name='Chapter I.1.a', parent=section11)

        create_l('Do you love all birds?', qtype=PollLineType.STRING, section=section111)

        with self.assertNoException():
            render = Template(
                r'{% load polls_tags %}'
                r'{% for node in nodes %}style="{% poll_node_css style node %}" {% endfor %}'
            ).render(Context({'nodes': SectionTree(pform), 'style': NodeStyle()}))

        self.assertEqual(
            'style="background-color: #BDD8E4;" '
            'style="background-color: #D8E5EB;" '
            'style="background-color: #D8E5EB;" '
            'style=""',
            render.strip(),
        )

    def test_stats_chart01(self):
        "No stat."
        user = self.create_user()
        pform = PollForm.objects.create(user=user, name='Form#1')

        self._get_formline_creator(pform=pform)('How many swallows?', qtype=PollLineType.INT)

        with self.assertNoException():
            render = Template(
                r'{% load polls_tags %}'
                r'{% for node in nodes %}{% poll_stats_chart node %}{% endfor %}'
            ).render(Context({'nodes': SectionTree(pform)}))

        self.assertEqual(escape(_('[An error occurred]')), render.strip())

    @skipIfCustomPollReply
    def test_stats_chart02(self):
        "INT stat."
        user = self.create_user()
        pform = PollForm.objects.create(user=user, name='Form#1')
        fline = self._get_formline_creator(pform=pform)(
            'How many swallows?', qtype=PollLineType.INT,
        )

        def create_reply(i, answer):
            reply = PollReply.objects.create(user=user, name=f'Reply#{i}', pform=pform)
            PollReplyLine.objects.create(
                preply=reply, pform_line=fline, type=fline.type, answer=answer,
            )

        create_reply(1, answer=12)
        create_reply(2, answer=23)

        with self.assertNoException():
            render = Template(
                r'{% load polls_tags %}'
                r'{% for node in nodes %}{% poll_stats_chart node %}{% endfor %}'
            ).render(Context({'nodes': StatsTree(pform)}))

        tree = self.get_html_tree(render)
        div_node = self.get_html_node_or_fail(tree, './/div')
        self.assertIn('poll-stat-chart', div_node.attrib.get('class'))

        script_node = self.get_html_node_or_fail(div_node, './/script')

        with self.assertNoException():
            chart_data = loads(script_node.text.replace('<!--', '').replace('-->', ''))

        self.assertIsInstance(chart_data, dict)

        with self.assertNoException():
            yaxis = chart_data['options']['axes']['yaxis']

        self.assertDictEqual(
            {
                'pad': 1.0,
                'renderer': 'jqplot.CategoryAxisRenderer',
                'tickRenderer': 'jqplot.AxisTickRenderer',
                'tickOptions': {
                    'textColor': 'black',
                    'fontSize': '8pt',
                },
                'labelOptions': {'show': False},
            },
            yaxis,
        )

        with self.assertNoException():
            values = chart_data['data']

        self.assertListEqual(
            [[[50.0, '12'], [50.0, '23']]],
            values,
        )

    @skipIfCustomPollReply
    def test_stats_chart03(self):
        "BOOL stat."
        user = self.create_user()
        pform = PollForm.objects.create(user=user, name='Form#1')
        fline = self._get_formline_creator(pform=pform)(
            'Do you like swallows?', qtype=PollLineType.BOOL,
        )

        def create_reply(i, answer):
            reply = PollReply.objects.create(user=user, name=f'Reply#{i}', pform=pform)
            PollReplyLine.objects.create(
                preply=reply, pform_line=fline, type=fline.type, answer=answer,
            )

        create_reply(1, answer=True)
        create_reply(2, answer=False)

        with self.assertNoException():
            render = Template(
                r'{% load polls_tags %}'
                r'{% for node in nodes %}{% poll_stats_chart node %}{% endfor %}'
            ).render(Context({'nodes': StatsTree(pform)}))

        tree = self.get_html_tree(render)
        div_node = self.get_html_node_or_fail(tree, './/div')
        self.assertIn('poll-stat-chart', div_node.attrib.get('class'))

        script_node = self.get_html_node_or_fail(div_node, './/script')

        with self.assertNoException():
            chart_data = loads(script_node.text.replace('<!--', '').replace('-->', ''))

        self.assertIsInstance(chart_data, dict)

        with self.assertNoException():
            yaxis = chart_data['options']['axes']['yaxis']

        self.assertDictEqual(
            {
                'renderer': 'jqplot.CategoryAxisRenderer',
                'tickOptions': {'show': False},
                'labelOptions': {'show': False},
                'ticks': [''],
            },
            yaxis,
        )

        with self.assertNoException():
            values = chart_data['data']

        self.assertListEqual(
            [
                [[50.0, 1, f"{_('No')} \\u2212 50.0 %"]],
                [[50.0, 1, f"{_('Yes')} \\u2212 50.0 %"]]
            ],
            values,
        )
