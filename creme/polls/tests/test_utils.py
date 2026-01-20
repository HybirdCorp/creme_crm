from functools import partial

from django.utils.translation import gettext as _

from ..core import PollLineType
from ..models import PollFormLine, PollFormSection, PollReplyLine
from ..templatetags.polls_tags import poll_node_css, poll_node_number
from ..utils import NodeStyle, SectionTree, StatsTree
from .base import (
    PollForm,
    _PollsTestCase,
    skipIfCustomPollForm,
    skipIfCustomPollReply,
)


@skipIfCustomPollForm
class SectionTreeTestCase(_PollsTestCase):
    def test_empty(self):
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')

        with self.assertNumQueries(2):  # 1 for sections, 1 for lines
            stree = SectionTree(pform)

        with self.assertNumQueries(0):
            nodes = [*stree]

        self.assertEqual([], nodes)

    def test_filled(self):
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')

        create_section = partial(PollFormSection.objects.create, pform=pform)
        section2  = create_section(name='2',  order=2)
        section1  = create_section(name='1',  order=1)
        section11 = create_section(name='11', order=1, parent=section1)

        create_line = self._get_formline_creator(pform)
        line0    = create_line('What is the difference between a swallow?')
        line1    = create_line('Beware there are many traps', qtype=PollLineType.COMMENT)
        line1_1  = create_line('What type of swallow?', section=section1)
        line11_1 = create_line('Do you like swallows?', section=section11)
        line11_2 = create_line('Do you eat swallows?',  section=section11)

        with self.assertNumQueries(2):  # 1 for sections, 1 for lines
            stree = SectionTree(pform)

        with self.assertNumQueries(0):
            nodes = [*stree]

        self.assertListEqual(
            [line0, line1, section1, line1_1, section11, line11_1, line11_2, section2],
            nodes
        )
        self.assertFalse(nodes[0].is_section)
        self.assertTrue(nodes[2].is_section)
        self.assertEqual([0, 0, 0, 1, 1, 2, 2, 0], [node.deep for node in nodes])
        self.assertEqual([1, None, 1, 2, 1, 3, 4, 2], [node.number for node in nodes])

        # Templatetag
        style = NodeStyle()
        self.assertListEqual(
            ['1', 'None', 'I', '2', '1', '3', '4', 'II'],
            [poll_node_number(style, node) for node in nodes],
        )
        self.assertEqual('',                           poll_node_css(style, nodes[0]))
        self.assertEqual('background-color: #BDD8E4;', poll_node_css(style, nodes[2]))
        self.assertEqual('background-color: #D8E5EB;', poll_node_css(style, nodes[4]))

    def test_order(self):
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')

        create_section = partial(PollFormSection.objects.create, pform=pform)
        section1  = create_section(name='1',  order=1)
        section11 = create_section(name='11', order=1, parent=section1)
        section2  = create_section(name='2',  order=2)

        create_line = partial(PollFormLine.objects.create, pform=pform, type=PollLineType.STRING)
        line0    = create_line(question='What is the difference between a swallow ?', order=1)
        line1_1  = create_line(question='What type of swallow ?', section=section1,   order=2)
        # order inverted:
        line11_2 = create_line(question='Do you eat swallows ?',  section=section11,  order=4)
        line11_1 = create_line(question='Do you like swallows ?', section=section11,  order=3)

        with self.assertNumQueries(2):  # 1 for sections, 1 for lines
            stree = SectionTree(pform)

        with self.assertNumQueries(0):
            nodes = [*stree]

        self.assertListEqual(
            [line0, section1, line1_1, section11, line11_1, line11_2, section2],
            nodes,
        )
        self.assertFalse(nodes[0].is_section)
        self.assertTrue(nodes[1].is_section)
        self.assertListEqual([0, 0, 1, 1, 2, 2, 0], [node.deep for node in nodes])

    def test_disabled_lines(self):
        "Section tree: manage disabled lines."
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')

        create_line = self._get_formline_creator(pform)
        create_line('How do you eat swallows ?')
        create_line('What type of swallow ?', disabled=True)
        create_line('Do you like swallows ?')

        self.assertListEqual([1, None, 2], [node.number for node in SectionTree(pform)])

    def test_poll_reply(self):  # TODO: ReplySectionTree instead?
        user = self.login_as_root_and_get()
        pform  = PollForm.objects.create(user=user, name='Form#1')

        create_section = partial(PollFormSection.objects.create, pform=pform)
        fsection2  = create_section(name='2',  order=2)
        fsection1  = create_section(name='1',  order=1)
        fsection11 = create_section(name='11', order=1, parent=fsection1)

        create_line = partial(PollFormLine.objects.create, pform=pform, type=PollLineType.STRING)
        fline0    = create_line(question='What is the difference between a swallow?',  order=1)
        fline1_1  = create_line(question='What type of swallow?', section=fsection1,   order=2)
        fline11_2 = create_line(question='Do you eat swallows?',  section=fsection11,  order=4)
        fline11_1 = create_line(question='Do you like swallows?', section=fsection11,  order=3)

        preply = self._create_preply_from_pform(pform, 'Reply#1')

        with self.assertNumQueries(2):  # 1 for sections, 1 for lines
            stree = SectionTree(preply)

        with self.assertNumQueries(0):
            nodes = [*stree]

        with self.assertNoException():
            get_rline  = PollReplyLine.objects.get
            rline0     = get_rline(pform_line=fline0)
            rsection1  = preply.sections.get(name=fsection1)
            rline1_1   = get_rline(pform_line=fline1_1)
            rsection11 = preply.sections.get(name=fsection11)
            rline11_1  = get_rline(pform_line=fline11_1)
            rline11_2  = get_rline(pform_line=fline11_2)
            rsection2  = preply.sections.get(name=fsection2)

        self.assertListEqual(
            [rline0, rsection1, rline1_1, rsection11, rline11_1, rline11_2, rsection2],
            nodes
        )
        self.assertFalse(nodes[0].is_section)
        self.assertTrue(nodes[1].is_section)
        self.assertListEqual([0, 0, 1, 1, 2, 2, 0], [node.deep for node in nodes])


@skipIfCustomPollForm
@skipIfCustomPollReply
class StatsTreeTestCase(_PollsTestCase):
    def test_stats_tree(self):
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')

        create_line = self._get_formline_creator(pform)
        colors = [[1, 'White'], [2, 'Black'], [3, 'Green'], [4, 'Purple']]
        fline1 = create_line('What do you think about swallows?')
        fline2 = create_line('How many swallows have you seen?', qtype=PollLineType.INT)
        fline3 = create_line(
            'What type of swallow?',
            qtype=PollLineType.ENUM, choices=[[1, 'European'], [2, 'African']],
        )
        fline4 = create_line(
            'What are the best colors for a swallow?',
            qtype=PollLineType.MULTI_ENUM, choices=colors,
        )
        fline5 = create_line(
            'What is your preferred color for a swallow?',
            qtype=PollLineType.ENUM_OR_STRING, choices=colors,
        )

        preply1 = self._create_preply_from_pform(pform, 'Reply#1')
        preply2 = self._create_preply_from_pform(pform, 'Reply#2')
        self._create_preply_from_pform(pform, 'Reply#3')  # No answer --> no stats
        preply4 = self._create_preply_from_pform(pform, 'Reply#4')

        answer_1_1 = 'They are cool'
        answer_2_1 = 5
        self._fill_preply(
            preply1, answer_1_1, answer_2_1, 1, [1, 2], {'answer_0': 1, 'answer_1': ''},
        )

        answer_1_2 = 'They are very cool'
        self._fill_preply(
            preply2, answer_1_2, answer_2_1, 2, [1], {'answer_0': 0, 'answer_1': 'Blue'},
        )

        answer_1_4 = 'They are very very cool'
        answer_2_4 = 10
        self._fill_preply(
            preply4, answer_1_4, answer_2_4, 2, [1, 2, 4], {'answer_0': 0, 'answer_1': 'Red'},
        )

        with self.assertNumQueries(3):  # 1 for sections, 1 for lines, 1 for replies
            stree = StatsTree(pform)

        with self.assertNumQueries(0):
            nodes = [*stree]

        self.assertEqual([fline1, fline2, fline3, fline4, fline5], nodes)

        with self.assertNumQueries(0):
            node1, node2, node3, node4, node5 = nodes

        self.assertEqual(node1.answer_count, 0)
        self.assertFalse(node1.answer_stats)
        self.assertFalse(node1.answer_zeros)

        self.assertEqual(node2.answer_count, 3)
        self.assertCountEqual(
            [
                (answer_2_1, 2, round((2.0 * 100.0) / 3.0, 3)),
                (answer_2_4, 1, round((1.0 * 100.0) / 3.0, 3)),
            ],
            node2.answer_stats,
        )
        self.assertFalse(node2.answer_zeros)

        self.assertEqual(node3.answer_count, 3)
        self.assertCountEqual(
            [
                ('European', 1, round((1.0 * 100.0) / 3.0, 3)),
                ('African',  2, round((2.0 * 100.0) / 3.0, 3)),
            ],
            node3.answer_stats,
        )
        self.assertFalse(node3.answer_zeros)

        self.assertEqual(node4.answer_count, 6)
        self.assertCountEqual(
            [
                ('White',  3, round((3.0 * 100.0) / 6.0, 3)),
                ('Black',  2, round((2.0 * 100.0) / 6.0, 3)),
                ('Purple', 1, round((1.0 * 100.0) / 6.0, 3)),
            ],
            node4.answer_stats,
        )
        self.assertCountEqual(
            [('Green',  0, 0.0)],
            node4.answer_zeros,
        )

        self.assertEqual(node5.answer_count, 3)
        self.assertCountEqual(
            [
                ('White',   1, round((1.0 * 100.0) / 3.0, 3)),
                (_('Other'), 2, round((2.0 * 100.0) / 3.0, 3)),
            ],
            node5.answer_stats,
        )
        self.assertCountEqual(
            [
                ('Black',   0, 0.0),
                ('Green',   0, 0.0),
                ('Purple',  0, 0.0),
            ],
            node5.answer_zeros,
        )

# TODO: test ReplySectionTree
