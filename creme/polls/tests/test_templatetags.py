from functools import partial

from django.template import Context, Template
from django.utils.translation import gettext as _

from ..core import PollLineType
from ..models import PollFormLineCondition, PollFormSection
from ..utils import NodeStyle, SectionTree
from .base import PollForm, _PollsTestCase, skipIfCustomPollForm


@skipIfCustomPollForm
class PollsTagsTestCase(_PollsTestCase):
    def test_line_condition(self):
        user = self.get_root_user()
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
        user = self.get_root_user()
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
        user = self.get_root_user()
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
