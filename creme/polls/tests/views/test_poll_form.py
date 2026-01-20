from functools import partial
from json import dumps as json_dump
from json import loads as json_load

from django.urls import reverse
from django.utils.translation import gettext as _
from parameterized import parameterized

from creme.creme_core.gui.bricks import Brick
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.polls.bricks import PollFormLinesBrick, PollRepliesBrick
from creme.polls.core import PollLineType
from creme.polls.models import (
    PollFormLine,
    PollFormLineCondition,
    PollFormSection,
    PollType,
)
from creme.polls.tests.base import (
    PollForm,
    _PollsTestCase,
    skipIfCustomPollForm,
)
from creme.polls.utils import NodeStyle, StatsTree


@skipIfCustomPollForm
class PollFormViewsTestCase(BrickTestCaseMixin, _PollsTestCase):
    def test_detail_view(self):
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')

        response = self.assertGET200(pform.get_absolute_url())

        tree = self.get_html_tree(response.content)
        self.get_brick_node(tree, brick=PollFormLinesBrick)

        replies_node = self.get_brick_node(tree, brick=PollRepliesBrick)
        self.assertEqual(_('Replies'), self.get_brick_title(replies_node))
        self.assertBrickHeaderHasNoButton(
            self.get_brick_header_buttons(replies_node),
            reverse('polls__create_replies_from_pform', args=(pform.id,)),
        )

        hat_node = self.get_brick_node(tree, brick=Brick.GENERIC_HAT_BRICK_ID)
        self.assertListEqual(
            [
                reverse('polls__form_stats', args=(pform.id,)),
                pform.get_edit_absolute_url(),
                reverse('creme_core__pin_entity', args=(pform.id,)),
                pform.get_clone_absolute_url(),
                pform.get_delete_absolute_url(),
            ],
            [
                a.attrib.get('href')
                for a in hat_node.findall('.//a[@class="bar-button"]')
            ],
        )

    def test_creation(self):
        user = self.login_as_root_and_get()
        self.assertFalse(PollForm.objects.all())

        url = reverse('polls__create_form')
        self.assertGET200(url)

        name = 'Form#1'
        ptype = PollType.objects.all()[0]
        response = self.client.post(
            url,
            follow=True,
            data={
                'user': user.id,
                'name': name,
                'type': ptype.id,
            },
        )
        self.assertNoFormError(response)

        pform = self.get_object_or_fail(PollForm, name=name)
        self.assertEqual(user,  pform.user)
        self.assertEqual(ptype, pform.type)

    def test_edition(self):
        user = self.login_as_root_and_get()
        name = 'form#1'
        pform = PollForm.objects.create(user=user, name=name)

        url = pform.get_edit_absolute_url()
        self.assertGET200(url)

        name = name.title()
        ptype = PollType.objects.all()[0]
        response = self.client.post(
            url,
            follow=True,
            data={
                'user': user.id,
                'name': name,
                'type': ptype.id,
            },
        )
        self.assertNoFormError(response)

        pform = self.refresh(pform)
        self.assertEqual(user,  pform.user)
        self.assertEqual(name,  pform.name)
        self.assertEqual(ptype, pform.type)

    def test_listview(self):
        user = self.login_as_root_and_get()
        create_pform = partial(PollForm.objects.create, user=user)
        pform1 = create_pform(name='Form#1')
        pform2 = create_pform(name='Form#2')

        response = self.assertGET200(PollForm.get_lv_absolute_url())

        with self.assertNoException():
            pform_page = response.context['page_obj']

        self.assertEqual(2, pform_page.paginator.count)
        self.assertCountEqual([pform1, pform2], pform_page.object_list)

    def test_stats__empty(self):
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')
        response = self.assertGET200(self._build_stats_url(pform))
        self.assertTemplateUsed(response, 'polls/stats.html')

        get = response.context.get
        self.assertIsInstance(get('nodes'), StatsTree)
        self.assertIsInstance(get('style'), NodeStyle)

    def test_stats__filled(self):
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')

        create_line = self._get_formline_creator(pform)
        line1 = create_line('What type of swallow?')
        line2 = create_line('Do you eat swallows?')
        line3 = create_line('Do you like swallows?')

        response = self.assertGET200(self._build_stats_url(pform))
        self.assertContains(response, line1.question)
        self.assertContains(response, line2.question)
        self.assertContains(response, line3.question)


@skipIfCustomPollForm
class SectionViewsTestCase(BrickTestCaseMixin, _PollsTestCase):
    def test_creation(self):  # TODO: uniqueness of name ???
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')

        url = reverse('polls__create_form_section', args=(pform.id,))
        context = self.assertGET200(url).context
        self.assertEqual(
            _('New section for «{entity}»').format(entity=pform),
            context.get('title'),
        )
        self.assertEqual(PollFormSection.save_label, context.get('submit_label'))

        # ---
        name = 'Name of the Chapter 1'
        body = 'balabla'
        self.assertNoFormError(self.client.post(url, data={'name': name, 'body': body}))

        section = self.get_alone_element(pform.sections.all())
        self.assertIsInstance(section, PollFormSection)
        self.assertEqual(name, section.name)
        self.assertEqual(body, section.body)
        self.assertEqual(1,    section.order)

        # ---
        response = self.assertGET200(pform.get_absolute_url())

        brick_node = self.get_brick_node(
            self.get_html_tree(response.content), brick=PollFormLinesBrick,
        )
        self.assertBrickTitleEqual(
            brick_node,
            count=1,
            title='{count} Section',
            plural_title='{count} Sections',
        )

    def test_creation__second(self):
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')
        PollFormSection.objects.create(pform=pform, name='Name of the Chapter 1', order=1)

        name = 'Name of the Chapter 2'
        self.assertNoFormError(self.client.post(
            reverse('polls__create_form_section', args=(pform.id,)), data={'name': name}
        ))

        section = pform.sections.get(name=name)
        self.assertEqual(2, section.order)

    def test_creation__sub_section(self):
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')

        create_section = partial(PollFormSection.objects.create, pform=pform)
        create_section(name='Name of the Chapter 1', order=1)
        section_2 = create_section(name='Name of the Chapter 2', order=2)
        section_3 = create_section(name='Name of the Chapter 3', order=3)

        url = reverse('polls__create_child_form_section', args=(section_2.id,))
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/add-popup.html')

        context = response.context
        self.assertEqual(
            _('New sub-section for «{section}»').format(section=section_2.name),
            context.get('title'),
        )
        self.assertEqual(PollFormSection.save_label, context.get('submit_label'))

        # ---
        name = 'Name of the Chapter 2.1'
        self.assertNoFormError(self.client.post(url, data={'name': name}))

        with self.assertNoException():
            section = pform.sections.get(parent=section_2)

        self.assertEqual(name, section.name)
        self.assertEqual(3,    section.order)

        self.assertEqual(4, self.refresh(section_3).order)

    def test_creation__sub_section__regular_user(self):
        user = self.login_as_polls_user()
        self.add_credentials(user.role, all='*')

        pform = PollForm.objects.create(user=user, name='Form#1')
        section = PollFormSection.objects.create(
            pform=pform, name='Name of the Chapter 1', order=1,
        )
        self.assertGET200(
            reverse('polls__create_child_form_section', args=(section.id,))
        )

    def test_creation__sub_section__edition_perms(self):
        "CHANGE credentials needed."
        user = self.login_as_polls_user()
        self.add_credentials(user.role, all='!CHANGE')

        pform = PollForm.objects.create(user=user, name='Form#1')
        section = PollFormSection.objects.create(
            pform=pform, name='Name of the Chapter 1', order=1,
        )
        self.assertGET403(reverse('polls__create_child_form_section', args=(section.id,)))

    def test_edition(self):
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')

        name = 'introduction'
        section = PollFormSection.objects.create(pform=pform, name=name, order=1)

        url = section.get_edit_absolute_url()
        response = self.assertGET200(url)
        self.assertTemplateUsed(
            response, 'creme_core/generics/blockform/edit-popup.html'
        )
        self.assertEqual(
            _('Section for «{entity}»').format(entity=pform),
            response.context.get('title'),
        )

        name = name.title()
        body = 'Once upon a time...'
        self.assertNoFormError(self.client.post(url, data={'name': name, 'body': body}))

        section = self.refresh(section)
        self.assertEqual(name, section.name)
        self.assertEqual(body, section.body)


@skipIfCustomPollForm
class LineCreationViewsTestCase(BrickTestCaseMixin, _PollsTestCase):
    @staticmethod
    def _build_line_creation_url(pform):
        return reverse('polls__create_form_line', args=(pform.id,))

    @staticmethod
    def _build_line_creation_in_section_url(section):
        return reverse('polls__create_form_line_in_section', args=(section.id,))

    def _create_enum_line_from_view(self, *, user, choices, qtype=PollLineType.ENUM):
        pform = PollForm.objects.create(user=user, name='Form#1')
        response = self.client.post(
            self._build_line_creation_url(pform),
            data={
                'question': 'What are the main colors of a swallow?',
                'type':     qtype,
                'choices':  '\r\n'.join(choices),
            },
        )
        self.assertNoFormError(response)

        line = pform.lines.all()[0]
        self.assertEqual(qtype, line.type)

        return line

    def test_string(self):
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')

        url = self._build_line_creation_url(pform)
        response1 = self.assertGET200(url)

        context1 = response1.context
        self.assertEqual(
            _('New question for «{entity}»').format(entity=pform),
            context1.get('title'),
        )
        self.assertEqual(PollFormLine.save_label, context1.get('submit_label'))

        with self.assertNoException():
            fields = context1['form'].fields

        self.assertNotIn('index', fields)

        question = 'What is the difference between a swallow ?'
        qtype = PollLineType.STRING
        self.assertNoFormError(self.client.post(
            url, data={'question': question, 'type': qtype},
        ))

        line = self.get_alone_element(pform.lines.all())
        self.assertIsInstance(line, PollFormLine)
        self.assertEqual(question, line.question)
        self.assertEqual(1,        line.order)
        self.assertEqual(qtype,    line.type)
        self.assertIsNone(line.section)

        plt = line.poll_line_type
        desc = _('String')
        self.assertEqual(desc, plt.verbose_name)
        self.assertEqual(desc, plt.description)

        # ---
        response3 = self.assertGET200(pform.get_absolute_url())
        brick_node = self.get_brick_node(
            self.get_html_tree(response3.content),
            brick=PollFormLinesBrick
        )
        self.assertBrickTitleEqual(
            brick_node,
            count=1,
            title='{count} Question',
            plural_title='{count} Questions',
        )

    def test_text(self):
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')

        question = 'What is the difference between a swallow (argue) ?'
        qtype = PollLineType.TEXT
        self.assertNoFormError(self.client.post(
            self._build_line_creation_url(pform),
            data={'question': question, 'type': qtype},
        ))

        line = self.get_alone_element(pform.lines.all())
        self.assertIsInstance(line, PollFormLine)
        self.assertEqual(question, line.question)
        self.assertEqual(1,        line.order)
        self.assertEqual(qtype,    line.type)
        self.assertIsNone(line.section)

        plt = line.poll_line_type
        desc = _('Text area')
        self.assertEqual(desc, plt.verbose_name)
        self.assertEqual(desc, plt.description)

    def test_int(self):
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')

        question = 'What is the size a swallow ? (cm)'
        qtype = PollLineType.INT
        self.assertNoFormError(self.client.post(
            self._build_line_creation_url(pform),
            data={
                'question': question,
                'type':     qtype,
                'order':    2,
            },
        ))

        line = pform.lines.get(question=question)
        self.assertEqual(1,     line.order)
        self.assertEqual(qtype, line.type)
        self.assertIsNone(line.type_args)

        plt = line.poll_line_type
        desc = _('Integer')
        self.assertEqual(desc, plt.verbose_name)
        self.assertEqual(desc, plt.description)

        self.assertIsNone(plt.get_choices())
        self.assertIsNone(plt.get_editable_choices())

    def test_int__lower_bound(self):
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')

        lower_bound = 0
        response = self.client.post(
            self._build_line_creation_url(pform),
            data={
                'question':    'What is the size a swallow? (cm)',
                'type':        PollLineType.INT,
                'lower_bound': lower_bound,
            },
        )
        self.assertNoFormError(response)

        line = pform.lines.all()[0]
        self.assertDictEqual({'lower_bound': lower_bound}, json_load(line.type_args))
        self.assertEqual(
            _('Integer greater than {min_value}').format(min_value=lower_bound),
            str(line.poll_line_type.description),
        )

    def test_int__upper_bound(self):
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')

        upper_bound = 10
        response = self.client.post(
            self._build_line_creation_url(pform),
            data={
                'question':    'What is the size a swallow ? (cm)',
                'type':        PollLineType.INT,
                'upper_bound': upper_bound,
            },
        )
        self.assertNoFormError(response)

        line = pform.lines.all()[0]
        self.assertDictEqual({'upper_bound': upper_bound}, json_load(line.type_args))
        self.assertEqual(
            _('Integer less than {max_value}').format(max_value=upper_bound),
            str(line.poll_line_type.description),
        )

    def test_int__bounds(self):
        "Upper bound & lower bound."
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')

        lower_bound = 1
        upper_bound = 15
        response = self.client.post(
            self._build_line_creation_url(pform),
            data={
                'question':    'What is the size a swallow? (cm)',
                'type':        PollLineType.INT,
                'lower_bound': lower_bound,
                'upper_bound': upper_bound,
            },
        )
        self.assertNoFormError(response)

        line = pform.lines.all()[0]
        self.assertDictEqual(
            {'lower_bound': lower_bound, 'upper_bound': upper_bound},
            json_load(line.type_args),
        )
        self.assertEqual(
            _('Integer between {min_value} and {max_value}').format(
                min_value=lower_bound,
                max_value=upper_bound,
            ),
            str(line.poll_line_type.description),
        )

    def test_int__bounds__error(self):
        "Validation error: upper bound > lower bound."
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')

        def post(lower_bound, upper_bound):
            response = self.assertPOST200(
                self._build_line_creation_url(pform),
                data={
                    'question':    'What is the size a swallow ? (cm)',
                    'type':        PollLineType.INT,
                    'lower_bound': lower_bound,
                    'upper_bound': upper_bound,
                },
            )
            self.assertFormError(
                self.get_form_or_fail(response),
                field=None,
                errors=_('The upper bound must be greater than the lower bound.'),
            )

        post(10, 3)
        post(4, 4)

    def test_bool(self):
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')
        question = 'Have you ever seen a knight of the Ni ?'
        qtype = PollLineType.BOOL
        self.assertNoFormError(self.client.post(
            self._build_line_creation_url(pform),
            data={'question': question, 'type': qtype},
        ))

        line = pform.lines.get(question=question)
        self.assertEqual(qtype, line.type)
        self.assertIsNone(line.type_args)

        plt = line.poll_line_type
        desc = _('Boolean (Yes/No)')
        self.assertEqual(desc, plt.verbose_name)
        self.assertEqual(desc, plt.description)

        self.assertCountEqual(plt.get_choices(), [(0, _('No')), (1, _('Yes'))])
        self.assertIsNone(plt.get_editable_choices())

        self.assertHasNoAttr(plt, 'get_deleted_choices')

    def test_date(self):
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')
        question = 'When did you see a swallow for the last time ?'
        qtype = PollLineType.DATE
        self.assertNoFormError(self.client.post(
            self._build_line_creation_url(pform),
            data={'question': question, 'type': qtype},
        ))

        line = pform.lines.get(question=question)
        self.assertEqual(qtype, line.type)
        self.assertIsNone(line.type_args)

        plt = line.poll_line_type
        desc = _('Date')
        self.assertEqual(desc, plt.verbose_name)
        self.assertEqual(desc, plt.description)

        self.assertIsNone(plt.get_choices())
        self.assertIsNone(plt.get_editable_choices())

    def test_hour(self):
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')
        question = 'Where did you see a swallow for the last time ?'
        qtype = PollLineType.HOUR
        self.assertNoFormError(self.client.post(
            self._build_line_creation_url(pform),
            data={'question': question, 'type': qtype},
        ))

        line = pform.lines.get(question=question)
        self.assertEqual(qtype, line.type)
        self.assertIsNone(line.type_args)

        plt = line.poll_line_type
        desc = _('Hour')
        self.assertEqual(desc, plt.verbose_name)
        self.assertEqual(desc, plt.description)

        self.assertIsNone(plt.get_choices())
        self.assertIsNone(plt.get_editable_choices())

    def test_choices(self):
        user = self.login_as_root_and_get()
        choices = [[1, 'White'], [2, 'Black'], [3, 'Green']]
        line = self._create_enum_line_from_view(
            user=user, choices=[c[1] for c in choices], qtype=PollLineType.ENUM,
        )
        self.assertEqual({'choices': choices}, json_load(line.type_args))

        plt = line.poll_line_type
        self.assertEqual(choices, plt.get_choices())
        self.assertEqual(choices, plt.get_editable_choices())
        self.assertEqual(_('Choice list'), plt.verbose_name)
        self.assertEqual(
            _('Choice list ({})').format('White / Black / Green'),
            plt.description,
        )

    def test_choices__error(self):
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')

        def post(*choices):
            response = self.assertPOST200(
                self._build_line_creation_url(pform),
                data={
                    'question': 'What is the main color of a swallow ?',
                    'type':     PollLineType.ENUM,
                    'choices':  '\n'.join(choices),
                },
            )
            self.assertFormError(
                self.get_form_or_fail(response),
                field=None, errors=_('Give 2 choices at least.'),
            )

        post()
        post('White')
        post(' ', '  ')

    def test_multi_choices(self):
        user = self.login_as_root_and_get()
        line = self._create_enum_line_from_view(
            user=user,
            choices=['White', 'Black', 'Green', 'Purple'],
            qtype=PollLineType.MULTI_ENUM,
        )
        plt = line.poll_line_type
        choices = [[1, 'White'], [2, 'Black'], [3, 'Green'], [4, 'Purple']]
        self.assertEqual(choices, plt.get_choices())
        self.assertEqual(choices, plt.get_editable_choices())
        self.assertEqual(_('Multiple choice list'), plt.verbose_name)
        self.assertEqual(
            _('Multiple choice list ({})').format('White / Black / Green / Purple'),
            plt.description,
        )

    def test_multi_choices__error(self):
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')

        def post(*choices):
            response = self.assertPOST200(
                self._build_line_creation_url(pform),
                data={
                    'question': 'What are the main colors of a swallow ?',
                    'type':     PollLineType.MULTI_ENUM,
                    'choices':  '\n'.join(choices),
                },
            )
            self.assertFormError(
                self.get_form_or_fail(response),
                field=None, errors=_('Give 2 choices at least.'),
            )

        post()
        post('White')
        post(' ', '  ')

    def test_free_choice(self):
        user = self.login_as_root_and_get()
        line = self._create_enum_line_from_view(
            user=user,
            choices=['White', 'Black', 'Green', 'Orange'],
            qtype=PollLineType.ENUM_OR_STRING,
        )
        plt = line.poll_line_type
        choices = [[1, 'White'], [2, 'Black'], [3, 'Green'], [4, 'Orange']]
        self.assertEqual([(0, _('Other')), *choices], plt.get_choices())
        self.assertEqual(choices,                     plt.get_editable_choices())

        self.assertFalse(plt.get_deleted_choices())
        self.assertEqual(_('Choice list with free choice'), plt.verbose_name)
        self.assertEqual(
            _('Choice list with free choice ({})').format('White / Black / Green / Orange'),
            plt.description,
        )

    def test_comment(self):
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')
        question = 'Your next answers must rhyme'
        qtype = PollLineType.COMMENT
        self.assertNoFormError(self.client.post(
            self._build_line_creation_url(pform),
            data={'question': question, 'type': qtype},
        ))

        line = pform.lines.get(question=question)
        self.assertEqual(qtype, line.type)
        self.assertIsNone(line.type_args)

        plt = line.poll_line_type
        desc = _('Comment')
        self.assertEqual(desc, plt.verbose_name)
        self.assertEqual(desc, plt.description)

        self.assertIsNone(plt.get_choices())
        self.assertIsNone(plt.get_editable_choices())

    def test_inserted__end_of_section(self):
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')
        self._get_formline_creator(pform)('What is the matter ?')

        url = self._build_line_creation_url(pform)
        response = self.client.get(url)

        with self.assertNoException():
            order_field = response.context['form'].fields['index']

        self.assertListEqual(
            [
                (0, _('Start of section')),
                (1, _('End of section')),
            ],
            order_field.choices,
        )
        self.assertEqual(1, order_field.initial)

        question = 'What is the size a swallow ? (cm)'
        self.assertNoFormError(self.client.post(
            url,
            data={
                'question': question,
                'type':     PollLineType.INT,
                'index':    1,
            },
        ))
        self.assertEqual(2, pform.lines.get(question=question).order)

    def test_inserted__start_of_section(self):
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')
        line = self._get_formline_creator(pform)('What is the matter ?')

        question = 'What is the size a swallow ? (cm)'
        self.assertNoFormError(self.client.post(
            self._build_line_creation_url(pform),
            data={
                'question': question,
                'type':     PollLineType.INT,
                'index':    0,
            },
        ))
        self.assertEqual(1, pform.lines.get(question=question).order)
        self.assertEqual(2, self.refresh(line).order)

    def test_add_to_section(self):
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')
        section = PollFormSection.objects.create(pform=pform, name='Section I')

        url = self._build_line_creation_in_section_url(section)
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/add-popup.html')

        context = response.context
        self.assertEqual(
            _('New question for section «{section}»').format(section=section.name),
            context.get('title'),
        )
        self.assertEqual(PollFormLine.save_label, context.get('submit_label'))

        # ---
        question = 'What is the size a swallow ? (cm)'
        qtype = PollLineType.INT
        self.assertNoFormError(
            self.client.post(url, data={'question': question, 'type': qtype}),
        )

        with self.assertNoException():
            line = pform.lines.get(question=question)

        self.assertEqual(section, line.section)
        self.assertEqual(qtype,   line.type)
        self.assertEqual(1,       line.order)

    def test_add_to_section__orders(self):
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')

        create_section = partial(PollFormSection.objects.create, pform=pform)
        section1 = create_section(name='Section I',  order=1)
        section2 = create_section(name='Section II', order=2)

        create_line = self._get_formline_creator(pform)
        line1 = create_line('Question 0',   section=None)
        line2 = create_line('Question 1.1', section=section1)
        line3 = create_line('Question 1.2', section=section1)
        line4 = create_line('Question 2.1', section=section2)
        line5 = create_line('Question 2.2', section=section2)
        line6 = create_line('Question 2.3', section=section2)

        question = 'What is the size a swallow ? (cm)'
        response = self.client.post(
            self._build_line_creation_in_section_url(section1),
            data={
                'question': question,
                'type':     PollLineType.INT,
                'index':    2,  # At the end
            },
        )
        self.assertNoFormError(response)

        with self.assertNoException():
            line = pform.lines.get(question=question)

        self.assertEqual(4, line.order)

        self.assertEqual(1, self.refresh(line1).order)
        self.assertEqual(2, self.refresh(line2).order)
        self.assertEqual(3, self.refresh(line3).order)
        self.assertEqual(5, self.refresh(line4).order)  # <===== not 4
        self.assertEqual(6, self.refresh(line5).order)
        self.assertEqual(7, self.refresh(line6).order)

    def test_add_to_section__empty_section(self):
        "Order (empty section, but not first line)."
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')

        create_section = partial(PollFormSection.objects.create, pform=pform)
        section1   = create_section(name='Section I', order=1)
        section1_1 = create_section(name='Section 1', order=2, parent=section1)
        section1_2 = create_section(name='Section 2', order=3, parent=section1)

        create_line = self._get_formline_creator(pform)
        line1 = create_line('Question 0',     section=None)
        line2 = create_line('Question I.a',   section=section1)
        line3 = create_line('Question I.b',   section=section1)
        line4 = create_line('Question I.2.a', section=section1_2)

        question = 'Question I.1.a'
        response = self.client.post(
            self._build_line_creation_in_section_url(section1_1),
            data={'question': question, 'type': PollLineType.INT},
        )
        self.assertNoFormError(response)

        with self.assertNoException():
            line = pform.lines.get(question=question)

        self.assertEqual(4, line.order)

        self.assertEqual(1, self.refresh(line1).order)
        self.assertEqual(2, self.refresh(line2).order)
        self.assertEqual(3, self.refresh(line3).order)
        self.assertEqual(5, self.refresh(line4).order)

    def test_add_to_section__regular_user(self):
        user = self.login_as_polls_user()
        self.add_credentials(user.role, all='*')

        pform = PollForm.objects.create(user=user, name='Form#1')
        section = PollFormSection.objects.create(pform=pform, name='Section I')

        self.assertGET200(self._build_line_creation_in_section_url(section))

    def test_add_to_section__edition_perms(self):
        "CHANGE credentials needed."
        user = self.login_as_polls_user()
        self.add_credentials(user.role, all='!CHANGE')

        pform = PollForm.objects.create(user=user, name='Form#1')
        section = PollFormSection.objects.create(pform=pform, name='Section I')

        self.assertGET403(self._build_line_creation_in_section_url(section))

    def test_add_to_section__inserted(self):
        "Insert a question between 2 other questions."
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')
        section = PollFormSection.objects.create(pform=pform, name='Section I')

        create_line = self._get_formline_creator(pform)
        line1 = create_line('Question I.1', section=section)
        line2 = create_line('Question I.2', section=section)
        line3 = create_line('Question I.3', section=section)

        url = self._build_line_creation_in_section_url(section)
        response = self.client.get(url)

        with self.assertNoException():
            order_field = response.context['form'].fields['index']

        msg_fmt = _('Before: «{question}» (#{number})')
        self.assertListEqual(
            [
                (0, _('Start of section')),
                (1,  msg_fmt.format(question=line2.question, number=2)),
                (2,  msg_fmt.format(question=line3.question, number=3)),
                (3, _('End of section')),
            ],
            order_field.choices,
        )
        self.assertEqual(3, order_field.initial)

        question = 'What is the size a swallow ? (cm)'
        self.assertNoFormError(self.client.post(
            url,
            data={
                'question': question,
                'type':     PollLineType.INT,
                'index':    2,
            },
        ))

        self.assertEqual(3, pform.lines.get(question=question).order)
        self.assertEqual(1, self.refresh(line1).order)
        self.assertEqual(2, self.refresh(line2).order)
        self.assertEqual(4, self.refresh(line3).order)


@skipIfCustomPollForm
class LineEditionTestCase(_PollsTestCase):
    def _create_enum_line(self, *, user, choices, qtype=PollLineType.ENUM, del_choices=None):
        kwargs = {} if not del_choices else {'del_choices': del_choices}
        create_l = self._get_formline_creator(
            PollForm.objects.create(user=user, name='Form#1'),
        )

        return create_l(
            'What are your favorite colors ?', qtype=qtype, choices=choices,
            **kwargs
        )

    def test_basic(self):
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')
        question = 'What is the difference between a swallow'
        qtype1 = PollLineType.STRING
        line = PollFormLine.objects.create(pform=pform, question=question, order=1, type=qtype1)

        url = line.get_edit_absolute_url()
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/edit-popup.html')

        context = response.context
        self.assertEqual(
            _('Question for «{entity}»').format(entity=pform),
            response.context.get('title'),
        )

        with self.assertNoException():
            fields = context['form'].fields

        self.assertNotIn('old_choices', fields)
        self.assertNotIn('new_choices', fields)

        question += ' ?'
        qtype2 = PollLineType.INT
        response = self.client.post(
            url,
            data={
                'question': question,
                'type':     qtype2,  # Should not be used
                'order':    3,  # Should not be used
            },
        )
        self.assertNoFormError(response)

        line = self.refresh(line)
        self.assertEqual(question, line.question)
        self.assertEqual(1,        line.order)  # Not changed !!
        self.assertEqual(qtype1,   line.type)  # Not changed !!

    def test_disabled(self):
        "Disabled line --> error."
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')
        line = PollFormLine.objects.create(
            pform=pform, question='How are you ?', order=1,
            type=PollLineType.STRING, disabled=True,
        )

        url = line.get_edit_absolute_url()
        self.assertGET404(url)
        self.assertPOST404(url, data={'question': line.question})

    def test_bool(self):
        "BOOL --> choices are not editable."
        user = self.login_as_root_and_get()
        line = PollFormLine.objects.create(
            pform=PollForm.objects.create(user=user, name='Form#1'),
            question='Are you ready ?', order=1, type=PollLineType.BOOL,
        )
        response = self.assertGET200(line.get_edit_absolute_url())

        with self.assertNoException():
            fields = response.context['form'].fields

        self.assertNotIn('old_choices', fields)
        self.assertNotIn('new_choices', fields)

    def test_description__multi_enum(self):
        user = self.login_as_root_and_get()
        line = self._create_enum_line(
            user=user,
            choices=[[2, 'Black'], [3, 'Red']],
            del_choices=[[1, 'White'], [4, 'Blue']],
            qtype=PollLineType.MULTI_ENUM,
        )
        self.assertEqual(
            _('Multiple choice list ({choices}) (deleted: {del_choices})').format(
                choices='Black / Red',
                del_choices='White / Blue',
            ),
            line.poll_line_type.description
        )

    def test_description__enum_or_string(self):
        user = self.login_as_root_and_get()
        line = self._create_enum_line(
            user=user,
            choices=[[2, 'Brown'], [3, 'Red']],
            del_choices=[[1, 'Grey'], [4, 'Blue']],
            qtype=PollLineType.ENUM_OR_STRING
        )
        self.assertEqual(
            _('Choice list with free choice ({choices}) (deleted: {del_choices})').format(
                choices='Brown / Red',
                del_choices='Grey / Blue',
            ),
            line.poll_line_type.description
        )

    def test_choices(self):
        "ENUM."
        user = self.login_as_root_and_get()
        line = self._create_enum_line(user=user, choices=[[1, 'White'], [2, 'black']])
        url = line.get_edit_absolute_url()
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields
            old_choices = fields['old_choices'].content
            fields['new_choices']  # NOQA

        self.assertEqual(['White', 'black'], old_choices)

        response = self.client.post(
            url,
            data={
                'question':     line.question,
                'new_choices': '\r\n'.join(['Green', 'Purple']),

                'old_choices_check_0': 'on',
                'old_choices_value_0': 'White',  # Not changed

                'old_choices_check_1': 'on',
                'old_choices_value_1': 'Black ',  # s/b/B + ' '
            },
        )
        self.assertNoFormError(response)
        self.assertDictEqual(
            {'choices': [[1, 'White'], [2, 'Black'], [3, 'Green'], [4, 'Purple']]},
            self.refresh(line).poll_line_type._args,
        )

    def test_choices__deletion(self):
        "Delete some choices."
        user = self.login_as_root_and_get()
        line = self._create_enum_line(user=user, choices=[[1, 'White'], [2, 'Black'], [3, 'Red']])
        response = self.client.post(
            line.get_edit_absolute_url(),
            data={
                'question':    line.question,
                'new_choices': 'Cyan',

                # 'old_choices_check_0': '',  # deleted
                'old_choices_value_0': 'White',

                'old_choices_check_1': 'on',
                'old_choices_value_1': 'Yellow',  # changed

                # 'old_choices_check_2': '',  # deleted too
                'old_choices_value_2': 'Red',
            },
        )
        self.assertNoFormError(response)

        plt = self.refresh(line).poll_line_type
        self.assertDictEqual(
            {
                'choices':     [[2, 'Yellow'], [4, 'Cyan']],
                'del_choices': [[1, 'White'], [3, 'Red']],
            },
            plt._args,
        )
        self.assertEqual(
            _('Choice list ({choices}) (deleted: {del_choices})').format(
                choices='Yellow / Cyan',
                del_choices='White / Red',
            ),
            plt.description,
        )

    def test_choices__remove_first(self):
        "With removed choices at beginning."
        user = self.login_as_root_and_get()
        line = self._create_enum_line(
            user=user,
            choices=[[2, 'Black'], [3, 'Red']],
            del_choices=[[1, 'White'], [4, 'Blue']],
        )
        response = self.client.post(
            line.get_edit_absolute_url(),
            data={
                'question':    line.question,
                'new_choices': 'Magenta',

                'old_choices_check_0': 'on',
                'old_choices_value_0': 'Black',  # unchanged

                # 'old_choices_check_1': '',
                'old_choices_value_1': 'Red',  # deleted
            },
        )
        self.assertNoFormError(response)
        self.assertDictEqual(
            {
                'choices':     [[2, 'Black'], [5, 'Magenta']],
                'del_choices': [[1, 'White'], [4, 'Blue'], [3, 'Red']],
            },
            self.refresh(line).poll_line_type._args,
        )

    def test_choices__not_empty(self):
        "Assert choices are not empty."
        user = self.login_as_root_and_get()
        line = self._create_enum_line(user=user, choices=[[1, 'White'], [2, 'Black'], [3, 'Red']])
        response = self.assertPOST200(
            line.get_edit_absolute_url(),
            data={
                'question': line.question,

                'old_choices_check_0': 'on',
                'old_choices_value_0': 'White',

                'old_choices_check_1': 'on',
                'old_choices_value_1': ' ',  # Empty  (after stripping) !!
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field='old_choices', errors=_('Choices can not be empty.'),
        )

    def test_choices__multi(self):
        "MULTI_ENUM."
        user = self.login_as_root_and_get()
        line = self._create_enum_line(
            user=user, choices=[[1, 'White'], [2, 'black']], qtype=PollLineType.MULTI_ENUM,
        )
        response = self.assertGET200(line.get_edit_absolute_url())

        with self.assertNoException():
            fields = response.context['form'].fields
            old_choices = fields['old_choices'].content
            fields['new_choices']  # NOQA

        self.assertEqual(['White', 'black'], old_choices)

    def test_choices__free_choice(self):
        "ENUM_OR_STRING."
        user = self.login_as_root_and_get()
        line = self._create_enum_line(
            user=user, choices=[[1, 'White'], [2, 'black']], qtype=PollLineType.ENUM_OR_STRING,
        )
        response = self.assertGET200(line.get_edit_absolute_url())

        with self.assertNoException():
            fields = response.context['form'].fields
            old_choices = fields['old_choices'].content
            fields['new_choices']  # NOQA

        self.assertEqual(['White', 'black'], old_choices)

    def test_choices__with_conditions__not_used(self):
        "Delete some choices (NOT used in conditions)."
        user = self.login_as_root_and_get()
        line1, line2, line3 = self._create_pform_with_3_lines_for_conditions(user=user)

        # We use choice 'A little bit' for condition
        PollFormLineCondition.objects.create(
            line=line3, source=line1, raw_answer='1',
            operator=PollFormLineCondition.EQUALS,
        )

        response = self.client.post(
            line1.get_edit_absolute_url(),
            data={
                'question':    line1.question,
                'new_choices': 'Passionately',

                'old_choices_check_0': 'on',
                'old_choices_value_0': 'A little bit',

                # 'old_choices_check_1': '', #we delete 'A lot'
                'old_choices_value_1': 'A lot',
            },
        )
        self.assertNoFormError(response)

        choices = [[1, 'A little bit'], [3, 'Passionately']]
        del_choices = [[2, 'A lot']]
        line1 = self.refresh(line1)
        self.assertDictEqual(
            {'choices': choices, 'del_choices': del_choices},
            json_load(line1.type_args),
        )

        plt = line1.poll_line_type
        self.assertEqual(choices,     plt.get_choices())
        self.assertEqual(del_choices, plt.get_deleted_choices())

    def test_choices__with_conditions__used(self):
        "Delete some choices (used in conditions)."
        user = self.login_as_root_and_get()
        line1, line2, line3 = self._create_pform_with_3_lines_for_conditions(user=user)

        # We use choice 'A little bit' for condition
        PollFormLineCondition.objects.create(
            line=line3, source=line1, raw_answer='1',
            operator=PollFormLineCondition.EQUALS,
        )

        response = self.assertPOST200(
            line1.get_edit_absolute_url(),  # TODO: factorise ?
            data={
                'question':    line1.question,
                'new_choices': 'Passionately',

                # 'old_choices_check_0': '', #we delete 'A little bit'
                'old_choices_value_0': 'A little bit',

                'old_choices_check_1': 'on',
                'old_choices_value_1': 'A lot',
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field='old_choices',
            errors=_(
                'You can not delete the choice "%(choice)s" because it '
                'is used in a condition by the question "%(question)s".'
            ) % {
                'choice': 'A little bit',
                'question': line3.question,
            },
        )


@skipIfCustomPollForm
class ConditionEditionTestCase(_PollsTestCase):
    @staticmethod
    def _build_conditions_edition_url(line):
        return reverse('polls__edit_form_line_conditions', args=(line.id,))

    @classmethod
    def _conditions_formfield_entry(cls, source, choice):
        return {'source': source, 'choice': choice}

    @classmethod
    def _conditions_formfield_value(cls, source, choice):
        return json_dump([cls._conditions_formfield_entry(source, choice)])

    def _aux_conditions_edition__enum_or_string(self, choice, raw_answer):
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')

        create_line = self._get_formline_creator(pform)
        line1 = create_line(
            'How do you like parrots?',
            qtype=PollLineType.ENUM_OR_STRING,
            choices=[[1, 'A little bit'], [2, 'A lot']],
        )
        line2 = create_line('Do you love all birds?', conds_use_or=False)

        self.assertNoFormError(self.client.post(
            self._build_conditions_edition_url(line2),
            data={
                'use_or':     1,
                'conditions': self._conditions_formfield_value(source=line1.id, choice=choice),
            },
        ))

        condition = line2.conditions.get(source=line1)
        self.assertEqual(raw_answer, condition.raw_answer)

    def test_add__enum(self):
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')

        create_line = self._get_formline_creator(pform)
        line1 = create_line(
            'What is your favorite meal ?',
            qtype=PollLineType.ENUM,
            choices=[[1, 'Spam'], [2, 'Grilled swallow']],
        )
        line2 = create_line('How can you love spam ?')
        self.assertIsNone(line2.conds_use_or)

        url = self._build_conditions_edition_url(line2)
        self.assertGET200(url)

        # ttype = 1  #TODO: 'display if' 'display except if'
        self.assertNoFormError(self.client.post(
            url,
            data={
                # 'type':      ttype,  # TODO
                'use_or':     1,
                'conditions': self._conditions_formfield_value(source=line1.id, choice=1),
            },
        ))

        line2 = self.refresh(line2)
        self.assertIs(line2.conds_use_or, True)
        # self.assertEqual(ttype, line2.conds_type)  # TODO

        condition = self.get_alone_element(line2.conditions.all())
        self.assertEqual(line1, condition.source)
        self.assertEqual('1',   condition.raw_answer)

    def test_add__enum__several_conditions(self):
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')

        enum_kwargs = {
            'qtype': PollLineType.ENUM,
            'choices': [[1, 'Spam'], [2, 'Grilled swallow']],
        }
        create_l = self._get_formline_creator(pform)
        line1 = create_l('What is your favorite meal ?',      **enum_kwargs)
        line2 = create_l('What is your real favorite meal ?', **enum_kwargs)
        line3 = create_l('How can you love spam ?')

        response = self.client.post(
            self._build_conditions_edition_url(line3),
            data={
                'use_or':     0,
                'conditions': json_dump([
                    self._conditions_formfield_entry(source=line1.id, choice=1),
                    self._conditions_formfield_entry(source=line2.id, choice=1),
                ]),
            }
        )
        self.assertNoFormError(response)

        line3 = self.refresh(line3)
        self.assertIs(line3.conds_use_or, False)
        self.assertListEqual(
            [line1, line2],
            [cond.source for cond in line3.conditions.order_by('id')],
        )

    def test_add__multi_enum(self):
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')

        create_line = self._get_formline_creator(pform)
        line1 = create_line(
            'What nuts do you like ?',
            qtype=PollLineType.MULTI_ENUM,
            choices=[[1, 'Coco nuts'], [2, 'Peanuts']],
        )
        line2 = create_line('Do you love all types of nuts ?', conds_use_or=False)

        response = self.client.post(
            self._build_conditions_edition_url(line2),
            data={
                'use_or':     1,
                'conditions': self._conditions_formfield_value(source=line1.id, choice=2),
            },
        )
        self.assertNoFormError(response)

        condition = line2.conditions.get(source=line1)
        self.assertEqual(json_dump([2]), condition.raw_answer)

    @parameterized.expand([
        (1, '1'),
        (0, '0'),
        (2, '2', _('This choice is invalid.')),
    ])
    def test_add__bool(self, choice, raw_answer, error=None):
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')

        create_line = self._get_formline_creator(pform)
        line1 = create_line('Do you love swallows ?', qtype=PollLineType.BOOL)
        line2 = create_line('Describe your love')

        response = self.assertPOST200(
            self._build_conditions_edition_url(line2),
            data={
                'use_or':     1,
                'conditions': self._conditions_formfield_value(source=line1.id, choice=choice),
            },
        )

        if error:
            self.assertFormError(self.get_form_or_fail(response), field='conditions', errors=error)
        else:
            self.assertNoFormError(response)

            condition = self.get_alone_element(self.refresh(line2).conditions.all())
            self.assertEqual(line1,      condition.source)
            self.assertEqual(raw_answer, condition.raw_answer)

    def test_add__enum_or_string(self):
        self._aux_conditions_edition__enum_or_string(1, json_dump([1]))

    def test_add__enum_or_string__other(self):
        "'Other' choice."
        self._aux_conditions_edition__enum_or_string(0, json_dump([0]))

    # TODO: def test_creationXX(self): other types of question ?

    def test_add__source_after_destination(self):
        "The source can not be after the destination."
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')

        create_line = self._get_formline_creator(pform)
        line1 = create_line('How can you love spam?')
        line2 = create_line(
            'What is your favorite meal?',
            qtype=PollLineType.ENUM,
            choices=[[1, 'Spam'], [2, 'Grilled swallow']],
        )

        response = self.assertPOST200(
            self._build_conditions_edition_url(line1),
            data={
                'use_or':     1,
                'conditions': self._conditions_formfield_value(source=line2.id, choice=1),
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field='conditions', errors=_('This source is invalid.'),
        )

    def test_add__disabled_line(self):
        "Line is disabled --> error."
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')
        line = PollFormLine.objects.create(
            pform=pform, question='How can you love spam ?',
            order=1, type=PollLineType.STRING, disabled=True
        )
        url = self._build_conditions_edition_url(line)
        self.assertGET404(url)
        self.assertPOST404(url)

    def test_add__regular_user(self):
        user = self.login_as_polls_user()
        self.add_credentials(user.role, all='*')

        pform = PollForm.objects.create(user=user, name='Form#1')
        line = self._get_formline_creator(pform)('How can you love spam?')
        self.assertGET200(self._build_conditions_edition_url(line))

    def test_add__permissions_error(self):
        "CHANGE credentials needed."
        user = self.login_as_polls_user()
        self.add_credentials(user.role, all='!CHANGE')

        pform = PollForm.objects.create(user=user, name='Form#1')
        line = self._get_formline_creator(pform)('How can you love spam?')
        self.assertGET403(self._build_conditions_edition_url(line))

    def test_edit__add_n_change(self):
        "Add a condition & change the existing one."
        user = self.login_as_root_and_get()
        line1, line2, line3 = self._create_pform_with_3_lines_for_conditions(user=user)

        PollFormLineCondition.objects.create(
            line=line3, source=line1, raw_answer='1',
            operator=PollFormLineCondition.EQUALS
        )

        url = self._build_conditions_edition_url(line3)
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/add-popup.html')

        context = response.context
        self.assertEqual(
            _('Conditions for «{entity}»').format(entity=self.pform),
            context.get('title'),
        )
        self.assertEqual(_('Save the conditions'), context.get('submit_label'))

        # ---
        response = self.client.post(
            url,
            data={
                'use_or':     1,
                'conditions': json_dump([
                    self._conditions_formfield_entry(source=line1.id, choice=2),
                    self._conditions_formfield_entry(source=line2.id, choice=1),
                ]),
            },
        )
        self.assertNoFormError(response)

        line3 = self.refresh(line3)
        self.assertIs(line3.conds_use_or, True)
        self.assertListEqual(
            [(line1, '2'), (line2, '1')],
            [(cond.source, cond.raw_answer) for cond in line3.conditions.order_by('id')]
        )

    def test_edit__change_n_remove(self):
        "Change an existing condition & remove one."
        user = self.login_as_root_and_get()
        line1, line2, line3 = self._create_pform_with_3_lines_for_conditions(user=user)

        create_cond = partial(
            PollFormLineCondition.objects.create,
            line=line3, operator=PollFormLineCondition.EQUALS,
        )
        create_cond(source=line1, raw_answer='1')
        create_cond(source=line2, raw_answer='2')

        response = self.client.post(
            self._build_conditions_edition_url(line3),
            data={
                'use_or':     1,
                'conditions': self._conditions_formfield_value(source=line1.id, choice=2),
            },
        )
        self.assertNoFormError(response)

        condition = self.get_alone_element(line3.conditions.all())
        self.assertEqual(line1, condition.source)
        self.assertEqual('2',   condition.raw_answer)

    def test_edit__remove_all(self):
        "Remove all conditions."
        user = self.login_as_root_and_get()
        line1, line2, line3 = self._create_pform_with_3_lines_for_conditions(user=user)

        create_cond = partial(
            PollFormLineCondition.objects.create,
            line=line3, operator=PollFormLineCondition.EQUALS,
        )
        create_cond(source=line1, raw_answer='1')
        create_cond(source=line2, raw_answer='2')

        self.assertNoFormError(self.client.post(
            self._build_conditions_edition_url(line3),
            data={'use_or': 1, 'conditions': '[]'}
        ))
        self.assertFalse(line3.conditions.all())

    def test_edit__regular_user(self):
        user = self.login_as_polls_user()
        self.add_credentials(user.role, all='*')

        line1, line2, line3 = self._create_pform_with_3_lines_for_conditions(user=user)

        PollFormLineCondition.objects.create(
            line=line3, source=line1, raw_answer='1',
            operator=PollFormLineCondition.EQUALS,
        )
        self.assertGET200(self._build_conditions_edition_url(line3))

    def test_edit__permissions_error(self):
        "CHANGE credentials are needed."
        user = self.login_as_polls_user()
        self.add_credentials(user.role, all='!CHANGE')

        line1, line2, line3 = self._create_pform_with_3_lines_for_conditions(user=user)

        PollFormLineCondition.objects.create(
            line=line3, source=line1, raw_answer='1',
            operator=PollFormLineCondition.EQUALS,
        )
        self.assertGET403(self._build_conditions_edition_url(line3))

    # TODO: remove conditions --> update conds_use_or ?? (or remove 'None' feature)


@skipIfCustomPollForm
class LineDisablingTestCase(_PollsTestCase):
    @staticmethod
    def _build_line_disabling_url(line):
        return reverse('polls__disable_form_line', args=(line.id,))

    def _disable_line(self, line, ajax=False):
        kwargs = {} if not ajax else {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}

        return self.client.post(
            self._build_line_disabling_url(line), data={'id': line.id}, **kwargs
        )

    def test_basic(self):
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')
        line = PollFormLine.objects.create(
            pform=pform, type=PollLineType.INT,
            order=1, question='How old is this swallow ?'
        )
        self.assertFalse(line.disabled)

        url = self._build_line_disabling_url(line)
        self.assertGET404(url)  # Only POST
        self.assertRedirects(self._disable_line(line), pform.get_absolute_url())
        self.assertTrue(self.assertStillExists(line).disabled)

    def test_is_destination(self):
        "Disabled line depends on other lines."
        user = self.login_as_root_and_get()
        line1, line2, line3 = self._create_pform_with_3_lines_for_conditions(user=user)

        create_cond = partial(
            PollFormLineCondition.objects.create,
            line=line3, operator=PollFormLineCondition.EQUALS,
        )
        cond1 = create_cond(source=line1, raw_answer='1')
        cond2 = create_cond(source=line2, raw_answer='2')

        self.assertEqual(302, self._disable_line(line3).status_code)
        self.assertTrue(self.assertStillExists(line3).disabled)
        self.assertFalse(
            PollFormLineCondition.objects.filter(id__in=[cond1.id, cond2.id]).exists()
        )

    def test_is_source(self):
        "Disabled line has a line that depends on it."
        user = self.login_as_root_and_get()
        line2, line3 = self._create_pform_with_3_lines_for_conditions(user=user)[1:]
        cond = PollFormLineCondition.objects.create(
            line=line3, source=line2, raw_answer='1',
            operator=PollFormLineCondition.EQUALS,
        )

        self.assertEqual(403, self._disable_line(line2).status_code)
        self.assertFalse(self.assertStillExists(line2).disabled)
        self.assertStillExists(cond)

        # TODO: when 404 rendering is improved
        # self.assertIn(
        #     _('There is at least one other question which depends on this question.'),
        #     response.content
        # )

    def test_already_disabled(self):
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')
        line = PollFormLine.objects.create(
            pform=pform, type=PollLineType.INT,
            order=1, question='How old is this swallow ?',
            disabled=True,
        )
        self.assertEqual(403, self._disable_line(line).status_code)

    def test_ajax__is_destination(self):
        "Disabled line depends on other lines."
        user = self.login_as_root_and_get()
        line1, line2, line3 = self._create_pform_with_3_lines_for_conditions(user=user)

        create_cond = partial(
            PollFormLineCondition.objects.create,
            line=line3, operator=PollFormLineCondition.EQUALS,
        )
        cond1 = create_cond(source=line1, raw_answer='1')
        cond2 = create_cond(source=line2, raw_answer='2')

        self.assertEqual(200, self._disable_line(line3, ajax=True).status_code)
        self.assertTrue(self.assertStillExists(line3).disabled)
        self.assertDoesNotExist(cond1)
        self.assertDoesNotExist(cond2)

    def test_ajax__is_source(self):
        "Disabled line has a line that depends on it."
        user = self.login_as_root_and_get()
        line2, line3 = self._create_pform_with_3_lines_for_conditions(user=user)[1:]
        cond = PollFormLineCondition.objects.create(
            line=line3, source=line2, raw_answer='1',
            operator=PollFormLineCondition.EQUALS,
        )

        response = self._disable_line(line2, ajax=True)
        self.assertEqual(403, response.status_code)
        self.assertFalse(self.assertStillExists(line2).disabled)
        self.assertStillExists(cond)
        self.assertEqual(
            _('There is at least one other question which depends on this question.'),
            response.text,
        )


@skipIfCustomPollForm
class ChoicesTestCase(_PollsTestCase):
    @staticmethod
    def _build_choices_url(line):
        return reverse('polls__form_line_choices', args=(line.id,))

    def test_enum(self):
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')
        choices = [[1, 'White'], [2, 'Black'], [3, 'Green']]
        line = self._get_formline_creator(pform)(
            'What is your favorite color ?',
            qtype=PollLineType.ENUM, choices=choices,
        )

        response = self.assertGET200(self._build_choices_url(line))
        self.assertEqual(choices, response.json())

    def test_multi_enum(self):
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')
        choices = [
            [1, 'Red'],  [2, 'Green'],   [3, 'Blue'],
            [4, 'Cyan'], [5, 'Magenta'], [6, 'Yellow'],
        ]
        line = self._get_formline_creator(pform)(
            'What colors do you like ?',
            qtype=PollLineType.MULTI_ENUM, choices=choices,
        )
        response = self.assertGET200(self._build_choices_url(line))
        self.assertEqual(choices, response.json())

    def test_enum_or_string(self):
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')
        choices = [[1, 'Cat'], [2, 'Dog'], [3, 'Fish']]
        line = self._get_formline_creator(pform)(
            'What is your pet ?',
            qtype=PollLineType.ENUM_OR_STRING, choices=choices,
        )
        response = self.assertGET200(self._build_choices_url(line))
        self.assertListEqual([[0, _('Other')], *choices], response.json())

    def test_bool(self):
        user = self.login_as_root_and_get()
        line = PollFormLine.objects.create(
            pform=PollForm.objects.create(user=user, name='Form#1'),
            question='Do you love swallows ?',
            order=1, type=PollLineType.BOOL,
        )
        response = self.assertGET200(self._build_choices_url(line))
        self.assertEqual([[0, _('No')], [1, _('Yes')]], response.json())

    def test_bad_type(self):
        user = self.login_as_root_and_get()
        line = PollFormLine.objects.create(
            pform=PollForm.objects.create(user=user, name='Form#1'),
            question='What do you like ?',
            order=1, type=PollLineType.STRING,
        )
        self.assertGET404(self._build_choices_url(line))

    # TODO?
    # def test_inneredit_line(self):
    #     user = self.login()
    #     pform = PollForm.objects.create(user=user, name='Form#1')
    #     line = self._get_formline_creator(pform)(
    #         'How do you like swallows',
    #         qtype=PollLineType.ENUM,
    #         choices=[[1, 'A little bit'], [2, 'A lot']],
    #     )
    #
    #     build_uri = self.build_inneredit_uri
    #     field_name = 'question'
    #     uri = build_uri(line, field_name)
    #     self.assertGET200(uri)
    #
    #     question = line.question + ' ?'
    #     response = self.client.post(
    #         uri,
    #         data={
    #             # 'entities_lbl': [str(line)],
    #             # 'field_value':  question,
    #             field_name:  question,
    #         },
    #     )
    #     self.assertNoFormError(response)
    #     self.assertEqual(question, self.refresh(line).question)
    #
    #     self.assertGET404(build_uri(line, 'pform'))
    #     self.assertGET404(build_uri(line, 'type'))
