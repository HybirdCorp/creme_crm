from functools import partial
from json import dumps as json_dump
from json import loads as json_load

from django.contrib.contenttypes.models import ContentType
from django.test.utils import override_settings
from django.urls import reverse
from django.utils.translation import gettext as _
from parameterized import parameterized

from creme.creme_core.gui.bricks import Brick
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.creme_core.utils.translation import smart_model_verbose_name

from ..bricks import PollFormLinesBrick, PollRepliesBrick
from ..core import PollLineType
from ..models import (
    PollFormLine,
    PollFormLineCondition,
    PollFormSection,
    PollType,
)
from ..templatetags.polls_tags import (
    poll_line_condition,
    poll_node_css,
    poll_node_number,
)
from ..utils import NodeStyle, SectionTree
from .base import PollForm, _PollsTestCase, skipIfCustomPollForm

get_ct = ContentType.objects.get_for_model


@skipIfCustomPollForm
class PollFormsTestCase(BrickTestCaseMixin, _PollsTestCase):
    @classmethod
    def conds_formfield_entry(cls, source, choice):
        return {'source': source, 'choice': choice}

    @classmethod
    def conds_formfield_value(cls, source, choice):
        return json_dump([cls.conds_formfield_entry(source, choice)])

    @staticmethod
    def build_addline_url(pform):
        return reverse('polls__create_form_line', args=(pform.id,))

    @staticmethod
    def build_addline2section_url(section):
        return reverse('polls__create_form_line_in_section', args=(section.id,))

    @staticmethod
    def build_choices_url(line):
        return reverse('polls__form_line_choices', args=(line.id,))

    @staticmethod
    def build_deleteline_url():
        return reverse(
            'creme_core__delete_related_to_entity',
            args=(get_ct(PollFormLine).id,),
        )

    @staticmethod
    def build_deletesection_url():
        return reverse(
            'creme_core__delete_related_to_entity',
            args=(get_ct(PollFormSection).id,),
        )

    @staticmethod
    def build_disableline_url(line):
        return reverse('polls__disable_form_line', args=(line.id,))

    @staticmethod
    def build_editlineconditions_url(line):
        return reverse('polls__edit_form_line_conditions', args=(line.id,))

    def create_enum_line(self, *, user, choices, qtype=PollLineType.ENUM, del_choices=None):
        kwargs = {} if not del_choices else {'del_choices': del_choices}
        create_l = self._get_formline_creator(
            PollForm.objects.create(user=user, name='Form#1'),
        )

        return create_l(
            'What are your favorite colors ?', qtype=qtype, choices=choices,
            **kwargs
        )

    def create_enum_line_from_view(self, *, user, choices, qtype=PollLineType.ENUM):
        pform = PollForm.objects.create(user=user, name='Form#1')
        response = self.client.post(
            self.build_addline_url(pform),
            data={
                'question': 'What are the main colors of a swallow ?',
                'type':     qtype,
                'choices':  '\r\n'.join(choices),
            },
        )
        self.assertNoFormError(response)

        line = pform.lines.all()[0]
        self.assertEqual(qtype, line.type)

        return line

    def create_3_lines_4_conditions(self, user):
        self.pform = pform = PollForm.objects.create(user=user, name='Form#1')
        ENUM = PollLineType.ENUM
        create_l = self._get_formline_creator(pform=pform)
        choices = [[1, 'A little bit'], [2, 'A lot']]

        return (
            create_l('How do you like swallows ?', qtype=ENUM, choices=choices),
            create_l('How do you like parrots ?',  qtype=ENUM, choices=choices),
            create_l('Do you love all birds ?',    qtype=PollLineType.STRING, conds_use_or=False),
        )

    def delete_related(self, related, url, ajax=False):
        kwargs = {} if not ajax else {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}

        return self.client.post(url, data={'id': related.id}, **kwargs)

    def delete_line(self, line, ajax=False):
        return self.delete_related(line, self.build_deleteline_url(), ajax)

    def delete_section(self, section, ajax=False):
        return self.delete_related(section, self.build_deletesection_url(), ajax)

    def disable_line(self, line, ajax=False):
        kwargs = {} if not ajax else {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}

        return self.client.post(
            self.build_disableline_url(line), data={'id': line.id}, **kwargs
        )

    def test_detailview01(self):
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

    def test_createview01(self):
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

    def test_editview01(self):
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

    def test_listview01(self):
        user = self.login_as_root_and_get()
        create_pform = partial(PollForm.objects.create, user=user)
        pform1 = create_pform(name='Form#1')
        pform2 = create_pform(name='Form#2')

        response = self.assertGET200(PollForm.get_lv_absolute_url())

        with self.assertNoException():
            pform_page = response.context['page_obj']

        self.assertEqual(2, pform_page.paginator.count)
        self.assertCountEqual([pform1, pform2], pform_page.object_list)

    @override_settings(ENTITIES_DELETION_ALLOWED=True)
    def test_deleteview01(self):
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')
        url = pform.get_delete_absolute_url()
        redirection = PollForm.get_lv_absolute_url()
        self.assertRedirects(self.client.post(url), redirection)

        pform = self.assertStillExists(pform)
        self.assertTrue(pform.is_deleted)

        self.assertRedirects(self.client.post(url), redirection)
        self.assertDoesNotExist(pform)

    @override_settings(ENTITIES_DELETION_ALLOWED=True)
    def test_deleteview02(self):
        user = self.login_as_root_and_get()
        line1, line2, line3 = self.create_3_lines_4_conditions(user=user)
        pform = self.pform

        create_cond = partial(
            PollFormLineCondition.objects.create,
            line=line3, operator=PollFormLineCondition.EQUALS,
        )
        cond1 = create_cond(source=line1, raw_answer='1')
        cond2 = create_cond(source=line2, raw_answer='2')

        url = pform.get_delete_absolute_url()
        self.assertPOST200(url, follow=True)

        pform = self.assertStillExists(pform)
        self.assertTrue(pform.is_deleted)
        self.assertStillExists(line1)
        self.assertStillExists(cond1)

        self.assertPOST200(url, follow=True)
        self.assertDoesNotExist(pform)
        self.assertFalse(PollFormLine.objects.filter(id__in=[line1.id, line2.id, line3.id]))
        self.assertFalse(PollFormLineCondition.objects.filter(id__in=[cond1.id, cond2.id]))

    def test_add_section01(self):  # TODO: uniqueness of name ???
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

    def test_add_section02(self):
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')
        PollFormSection.objects.create(pform=pform, name='Name of the Chapter 1', order=1)

        name = 'Name of the Chapter 2'
        response = self.client.post(
            reverse('polls__create_form_section', args=(pform.id,)), data={'name': name}
        )
        self.assertNoFormError(response)

        section = pform.sections.get(name=name)
        self.assertEqual(2, section.order)

    def test_add_sub_section01(self):
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

    def test_add_sub_section02(self):
        "Not super-user"
        user = self.login_as_polls_user()
        self.add_credentials(user.role, all='*')

        pform = PollForm.objects.create(user=user, name='Form#1')
        section = PollFormSection.objects.create(
            pform=pform, name='Name of the Chapter 1', order=1,
        )
        self.assertGET200(
            reverse('polls__create_child_form_section', args=(section.id,))
        )

    def test_add_sub_section03(self):
        "CHANGE credentials needed."
        user = self.login_as_polls_user()
        self.add_credentials(user.role, all='!CHANGE')

        pform = PollForm.objects.create(user=user, name='Form#1')
        section = PollFormSection.objects.create(
            pform=pform, name='Name of the Chapter 1', order=1,
        )
        self.assertGET403(reverse('polls__create_child_form_section', args=(section.id,)))

    def test_edit_section(self):
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

    def test_delete_section01(self):
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')
        section = PollFormSection.objects.create(pform=pform, name='Introduction', order=1)

        self.assertGET405(self.build_deletesection_url())

        self.assertEqual([False], [node.has_line for node in SectionTree(pform)])

        self.assertEqual(200, self.delete_section(section, ajax=True).status_code)
        self.assertDoesNotExist(section)

    def test_delete_section02(self):
        "Deleted section has a line."
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')
        section = PollFormSection.objects.create(pform=pform, name='Introduction', order=1)
        line = self._get_formline_creator(pform)(
            'What is the matter ?',
            section=section,  # <=======
        )

        self.assertListEqual(
            [True], [node.has_line for node in SectionTree(pform) if node.is_section],
        )

        self.assertEqual(409, self.delete_section(section).status_code)
        self.assertStillExists(line)
        self.assertStillExists(section)

        # TODO: when 404 rendering is improved
        # self.assertIn(_('There is at least one question in this section.'), response.content)

    def test_delete_section03(self):
        "Empty sub-sections are deleted."
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')

        create_section = partial(PollFormSection.objects.create, pform=pform)
        section     = create_section(name='Chapter I',   order=1)
        sub_section = create_section(name='Chapter I.1', order=2, parent=section)

        self.assertListEqual(
            [False, False],
            [node.has_line for node in SectionTree(pform) if node.is_section],
        )

        self.assertRedirects(self.delete_section(section), pform.get_absolute_url())
        self.assertFalse(PollFormSection.objects.filter(pk__in=[section.pk, sub_section.pk]))

    def test_delete_section04(self):
        "Deleted section has a line (indirectly)."
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')

        create_section = partial(PollFormSection.objects.create, pform=pform)
        section      = create_section(name='Chapter I',   order=1)
        sub_section1 = create_section(name='Chapter I.1', order=2, parent=section)
        sub_section2 = create_section(name='Chapter I.2', order=3, parent=section)

        line = self._get_formline_creator(pform)(
            'What is the matter ?',
            section=sub_section1,  # <=======
        )

        self.assertListEqual(
            [True, True, False],
            [node.has_line for node in SectionTree(pform) if node.is_section],
        )

        response = self.delete_section(section, ajax=True)
        self.assertEqual(409, response.status_code)
        self.assertStillExists(section)
        self.assertStillExists(sub_section1)
        self.assertStillExists(sub_section2)
        self.assertStillExists(line)
        self.assertHTMLEqual(
            '<span>{message}</span><ul><li>{dependencies}</li></ul>'.format(
                message=_(
                    'This deletion cannot be performed because of the links '
                    'with some entities (& other elements):'
                ),
                dependencies=_('{count} {model}').format(
                    count=1,
                    model=smart_model_verbose_name(model=PollFormSection, count=1),
                )
            ),
            response.text,
        )

    def test_add_line_string01(self):
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')

        url = self.build_addline_url(pform)
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

    def test_add_line_text01(self):
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')

        question = 'What is the difference between a swallow (argue) ?'
        qtype = PollLineType.TEXT
        self.assertNoFormError(self.client.post(
            self.build_addline_url(pform),
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

    def test_add_line_int01(self):
        "Integer type."
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')

        question = 'What is the size a swallow ? (cm)'
        qtype = PollLineType.INT
        self.assertNoFormError(self.client.post(
            self.build_addline_url(pform),
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

    def test_add_line_int02(self):
        "Lower bound."
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')

        lower_bound = 0
        response = self.client.post(
            self.build_addline_url(pform),
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

    def test_add_line_int03(self):
        "Upper bound."
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')

        upper_bound = 10
        response = self.client.post(
            self.build_addline_url(pform),
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

    def test_add_line_int04(self):
        "Upper bound & lower bound."
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')

        lower_bound = 1
        upper_bound = 15
        response = self.client.post(
            self.build_addline_url(pform),
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

    def test_add_line_int05(self):
        "Validation error: upper bound > lower bound."
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')

        def post(lower_bound, upper_bound):
            response = self.assertPOST200(
                self.build_addline_url(pform),
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

    def test_add_line_bool01(self):
        "Boolean type."
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')
        question = 'Have you ever seen a knight of the Ni ?'
        qtype = PollLineType.BOOL
        self.assertNoFormError(self.client.post(
            self.build_addline_url(pform),
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

    def test_add_line_date01(self):
        "Date type."
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')
        question = 'When did you see a swallow for the last time ?'
        qtype = PollLineType.DATE
        self.assertNoFormError(self.client.post(
            self.build_addline_url(pform),
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

    def test_add_line_hour01(self):
        "Hour type."
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')
        question = 'Where did you see a swallow for the last time ?'
        qtype = PollLineType.HOUR
        self.assertNoFormError(self.client.post(
            self.build_addline_url(pform),
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

    def test_add_line_choices01(self):
        user = self.login_as_root_and_get()
        choices = [[1, 'White'], [2, 'Black'], [3, 'Green']]
        line = self.create_enum_line_from_view(
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

    def test_add_line_choices02(self):
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')

        def post(*choices):
            response = self.assertPOST200(
                self.build_addline_url(pform),
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

    def test_add_line_multichoices01(self):
        user = self.login_as_root_and_get()
        line = self.create_enum_line_from_view(
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

    def test_add_line_multichoices02(self):
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')

        def post(*choices):
            response = self.assertPOST200(
                self.build_addline_url(pform),
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

    def test_add_line_freechoice01(self):
        user = self.login_as_root_and_get()
        line = self.create_enum_line_from_view(
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

    def test_add_line_comment01(self):
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')
        question = 'Your next answers must rhyme'
        qtype = PollLineType.COMMENT
        self.assertNoFormError(self.client.post(
            self.build_addline_url(pform),
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

    def test_insert_line01(self):
        "End of section."
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')
        self._get_formline_creator(pform)('What is the matter ?')

        url = self.build_addline_url(pform)
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

    def test_insert_line02(self):
        "Start of section."
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')
        line = self._get_formline_creator(pform)('What is the matter ?')

        question = 'What is the size a swallow ? (cm)'
        self.assertNoFormError(self.client.post(
            self.build_addline_url(pform),
            data={
                'question': question,
                'type':     PollLineType.INT,
                'index':    0,
            },
        ))
        self.assertEqual(1, pform.lines.get(question=question).order)
        self.assertEqual(2, self.refresh(line).order)

    def test_add_line_to_section01(self):
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')
        section = PollFormSection.objects.create(pform=pform, name='Section I')

        url = self.build_addline2section_url(section)
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

    def test_add_line_to_section02(self):
        "Orders."
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
            self.build_addline2section_url(section1),
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

    def test_add_line_to_section03(self):
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
            self.build_addline2section_url(section1_1),
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

    def test_add_line_to_section04(self):
        "Not super-user."
        user = self.login_as_polls_user()
        self.add_credentials(user.role, all='*')

        pform = PollForm.objects.create(user=user, name='Form#1')
        section = PollFormSection.objects.create(pform=pform, name='Section I')

        self.assertGET200(self.build_addline2section_url(section))

    def test_add_line_to_section05(self):
        "CHANGE credentials needed."
        user = self.login_as_polls_user()
        self.add_credentials(user.role, all='!CHANGE')

        pform = PollForm.objects.create(user=user, name='Form#1')
        section = PollFormSection.objects.create(pform=pform, name='Section I')

        self.assertGET403(self.build_addline2section_url(section))

    def test_insert_line_to_section01(self):
        "Insert a question between 2 other questions"
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')
        section = PollFormSection.objects.create(pform=pform, name='Section I')

        create_line = self._get_formline_creator(pform)
        line1 = create_line('Question I.1', section=section)
        line2 = create_line('Question I.2', section=section)
        line3 = create_line('Question I.3', section=section)

        url = self.build_addline2section_url(section)
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

    def test_edit_line01(self):
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

    def test_edit_line02(self):
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

    def test_edit_line03(self):
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

    def test_edit_line_choices01(self):
        "ENUM."
        user = self.login_as_root_and_get()
        line = self.create_enum_line(user=user, choices=[[1, 'White'], [2, 'black']])
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

    def test_edit_line_choices02(self):
        "Delete some choices."
        user = self.login_as_root_and_get()
        line = self.create_enum_line(user=user, choices=[[1, 'White'], [2, 'Black'], [3, 'Red']])
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

    def test_edit_line_choices03(self):
        "With removed choices at beginning."
        user = self.login_as_root_and_get()
        line = self.create_enum_line(
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

    def test_edit_line_choices04(self):
        "Assert choices are not empty."
        user = self.login_as_root_and_get()
        line = self.create_enum_line(user=user, choices=[[1, 'White'], [2, 'Black'], [3, 'Red']])
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

    def test_edit_line_choices05(self):
        "MULTI_ENUM."
        user = self.login_as_root_and_get()
        line = self.create_enum_line(
            user=user, choices=[[1, 'White'], [2, 'black']], qtype=PollLineType.MULTI_ENUM,
        )
        response = self.assertGET200(line.get_edit_absolute_url())

        with self.assertNoException():
            fields = response.context['form'].fields
            old_choices = fields['old_choices'].content
            fields['new_choices']  # NOQA

        self.assertEqual(['White', 'black'], old_choices)

    def test_edit_line_choices06(self):
        "ENUM_OR_STRING."
        user = self.login_as_root_and_get()
        line = self.create_enum_line(
            user=user, choices=[[1, 'White'], [2, 'black']], qtype=PollLineType.ENUM_OR_STRING,
        )
        response = self.assertGET200(line.get_edit_absolute_url())

        with self.assertNoException():
            fields = response.context['form'].fields
            old_choices = fields['old_choices'].content
            fields['new_choices']  # NOQA

        self.assertEqual(['White', 'black'], old_choices)

    def test_edit_line_description01(self):
        "MULTI_ENUM."
        user = self.login_as_root_and_get()
        line = self.create_enum_line(
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

    def test_edit_line_description02(self):
        "ENUM_OR_STRING."
        user = self.login_as_root_and_get()
        line = self.create_enum_line(
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

    def test_edit_line_choices_with_conditions01(self):
        "Delete some choices (NOT used in conditions)."
        user = self.login_as_root_and_get()
        line1, line2, line3 = self.create_3_lines_4_conditions(user=user)

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

    def test_edit_line_choices_with_conditions02(self):
        "Delete some choices (NOT used in conditions)."
        user = self.login_as_root_and_get()
        line1, line2, line3 = self.create_3_lines_4_conditions(user=user)

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

    def test_delete_type(self):
        "Set to NULL."
        user = self.login_as_root_and_get()
        ptype = PollType.objects.create(name='Political poll')
        pform = PollForm.objects.create(user=user, name='Form#1', type=ptype)

        response = self.client.post(reverse(
            'creme_config__delete_instance',
            args=('polls', 'poll_type', ptype.id),
        ))
        self.assertNoFormError(response)

        job = self.get_deletion_command_or_fail(PollType).job
        job.type.execute(job)
        self.assertDoesNotExist(ptype)

        pform = self.assertStillExists(pform)
        self.assertIsNone(pform.type)

    def test_section_tree01(self):
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')

        with self.assertNumQueries(2):  # 1 for sections, 1 for lines
            stree = SectionTree(pform)

        with self.assertNumQueries(0):
            nodes = [*stree]

        self.assertEqual([], nodes)

    def test_section_tree02(self):
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')

        create_section = partial(PollFormSection.objects.create, pform=pform)
        section2  = create_section(name='2',  order=2)
        section1  = create_section(name='1',  order=1)
        section11 = create_section(name='11', order=1, parent=section1)

        create_line = self._get_formline_creator(pform)
        line0    = create_line('What is the difference between a swallow ?')
        line1    = create_line('Beware there are many traps', qtype=PollLineType.COMMENT)
        line1_1  = create_line('What type of swallow ?', section=section1)
        line11_1 = create_line('Do you like swallows ?', section=section11)
        line11_2 = create_line('Do you eat swallows ?',  section=section11)

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

    def test_section_tree03(self):
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

    def test_section_tree04(self):
        "Section tree: manage disabled lines."
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')

        create_line = self._get_formline_creator(pform)
        create_line('How do you eat swallows ?')
        create_line('What type of swallow ?', disabled=True)
        create_line('Do you like swallows ?')

        self.assertListEqual([1, None, 2], [node.number for node in SectionTree(pform)])

    def test_statsview01(self):
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')
        response = self.assertGET200(self._build_stats_url(pform))
        self.assertTemplateUsed(response, 'polls/stats.html')

        from ..utils import NodeStyle, StatsTree

        get = response.context.get
        self.assertIsInstance(get('nodes'), StatsTree)
        self.assertIsInstance(get('style'), NodeStyle)

    def test_statsview02(self):
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')

        create_line = self._get_formline_creator(pform)
        line1 = create_line('What type of swallow ?')
        line2 = create_line('Do you eat swallows ?')
        line3 = create_line('Do you like swallows ?')

        response = self.assertGET200(self._build_stats_url(pform))
        self.assertContains(response, line1.question)
        self.assertContains(response, line2.question)
        self.assertContains(response, line3.question)

    def test_add_line_conditions_enum01(self):
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

        url = self.build_editlineconditions_url(line2)
        self.assertGET200(url)

        # ttype = 1  #TODO: 'display if' 'display except if'
        self.assertNoFormError(self.client.post(
            url,
            data={
                # 'type':      ttype,  # TODO
                'use_or':     1,
                'conditions': self.conds_formfield_value(source=line1.id, choice=1),
            },
        ))

        line2 = self.refresh(line2)
        self.assertIs(line2.conds_use_or, True)
        # self.assertEqual(ttype, line2.conds_type)  # TODO

        condition = self.get_alone_element(line2.conditions.all())
        self.assertEqual(line1, condition.source)
        self.assertEqual('1',   condition.raw_answer)

    def test_add_line_conditions_enum02(self):
        "Several conditions"
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
            self.build_editlineconditions_url(line3),
            data={
                'use_or':     0,
                'conditions': json_dump([
                    self.conds_formfield_entry(source=line1.id, choice=1),
                    self.conds_formfield_entry(source=line2.id, choice=1),
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

    def test_add_line_conditions_not_super_user(self):
        user = self.login_as_polls_user()
        self.add_credentials(user.role, all='*')

        pform = PollForm.objects.create(user=user, name='Form#1')
        line = self._get_formline_creator(pform)('How can you love spam?')
        self.assertGET200(self.build_editlineconditions_url(line))

    def test_add_line_conditions_creds(self):
        "CHANGE credentials needed."
        user = self.login_as_polls_user()
        self.add_credentials(user.role, all='!CHANGE')

        pform = PollForm.objects.create(user=user, name='Form#1')
        line = self._get_formline_creator(pform)('How can you love spam?')
        self.assertGET403(self.build_editlineconditions_url(line))

    def test_add_line_conditions_multienum(self):
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
            self.build_editlineconditions_url(line2),
            data={
                'use_or':     1,
                'conditions': self.conds_formfield_value(source=line1.id, choice=2),
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
    def test_add_line_conditions_bool(self, choice, raw_answer, error=None):
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')

        create_line = self._get_formline_creator(pform)
        line1 = create_line('Do you love swallows ?', qtype=PollLineType.BOOL)
        line2 = create_line('Describe your love')

        response = self.assertPOST200(
            self.build_editlineconditions_url(line2),
            data={
                'use_or':     1,
                'conditions': self.conds_formfield_value(source=line1.id, choice=choice),
            },
        )

        if error:
            self.assertFormError(self.get_form_or_fail(response), field='conditions', errors=error)
        else:
            self.assertNoFormError(response)

            condition = self.get_alone_element(self.refresh(line2).conditions.all())
            self.assertEqual(line1,      condition.source)
            self.assertEqual(raw_answer, condition.raw_answer)

    def _aux_add_line_conditions_enumorchoice(self, choice, raw_answer):
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')

        create_line = self._get_formline_creator(pform)
        line1 = create_line(
            'How do you like parrots ?',
            qtype=PollLineType.ENUM_OR_STRING,
            choices=[[1, 'A little bit'], [2, 'A lot']],
        )
        line2 = create_line('Do you love all birds ?', conds_use_or=False)

        response = self.client.post(
            self.build_editlineconditions_url(line2),
            data={
                'use_or':     1,
                'conditions': self.conds_formfield_value(source=line1.id, choice=choice),
            },
        )
        self.assertNoFormError(response)

        condition = line2.conditions.get(source=line1)
        self.assertEqual(raw_answer, condition.raw_answer)

    def test_add_line_conditions_enumorchoice01(self):
        self._aux_add_line_conditions_enumorchoice(1, json_dump([1]))

    def test_add_line_conditions_enumorchoice02(self):
        "'Other' choice."
        self._aux_add_line_conditions_enumorchoice(0, json_dump([0]))

    # TODO: def test_add_line_conditionsXX(self): other types of question ?

    def test_add_line_conditions_error01(self):
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
            self.build_editlineconditions_url(line1),
            data={
                'use_or':     1,
                'conditions': self.conds_formfield_value(source=line2.id, choice=1),
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field='conditions', errors=_('This source is invalid.'),
        )

    def test_add_line_conditions_error02(self):
        "Line is disabled --> error."
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')
        line = PollFormLine.objects.create(
            pform=pform, question='How can you love spam ?',
            order=1, type=PollLineType.STRING, disabled=True
        )
        url = self.build_editlineconditions_url(line)
        self.assertGET404(url)
        self.assertPOST404(url)

    def test_edit_line_conditions01(self):
        "Add a condition & change the existing one."
        user = self.login_as_root_and_get()
        line1, line2, line3 = self.create_3_lines_4_conditions(user=user)

        PollFormLineCondition.objects.create(
            line=line3, source=line1, raw_answer='1',
            operator=PollFormLineCondition.EQUALS
        )

        url = self.build_editlineconditions_url(line3)
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
                    self.conds_formfield_entry(source=line1.id, choice=2),
                    self.conds_formfield_entry(source=line2.id, choice=1),
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

    def test_edit_line_conditions02(self):
        "Change an existing condition & remove one."
        user = self.login_as_root_and_get()
        line1, line2, line3 = self.create_3_lines_4_conditions(user=user)

        create_cond = partial(
            PollFormLineCondition.objects.create,
            line=line3, operator=PollFormLineCondition.EQUALS,
        )
        create_cond(source=line1, raw_answer='1')
        create_cond(source=line2, raw_answer='2')

        response = self.client.post(
            self.build_editlineconditions_url(line3),
            data={
                'use_or':     1,
                'conditions': self.conds_formfield_value(source=line1.id, choice=2),
            },
        )
        self.assertNoFormError(response)

        condition = self.get_alone_element(line3.conditions.all())
        self.assertEqual(line1, condition.source)
        self.assertEqual('2',   condition.raw_answer)

    def test_edit_line_conditions03(self):
        "Remove all conditions."
        user = self.login_as_root_and_get()
        line1, line2, line3 = self.create_3_lines_4_conditions(user=user)

        create_cond = partial(
            PollFormLineCondition.objects.create,
            line=line3, operator=PollFormLineCondition.EQUALS,
        )
        create_cond(source=line1, raw_answer='1')
        create_cond(source=line2, raw_answer='2')

        self.assertNoFormError(self.client.post(
            self.build_editlineconditions_url(line3),
            data={'use_or': 1, 'conditions': '[]'}
        ))
        self.assertFalse(line3.conditions.all())

    def test_edit_line_conditions04(self):
        "Not super-user."
        user = self.login_as_polls_user()
        self.add_credentials(user.role, all='*')

        line1, line2, line3 = self.create_3_lines_4_conditions(user=user)

        PollFormLineCondition.objects.create(
            line=line3, source=line1, raw_answer='1',
            operator=PollFormLineCondition.EQUALS,
        )
        self.assertGET200(self.build_editlineconditions_url(line3))

    def test_edit_line_conditions05(self):
        "CHANGE credentials are needed."
        user = self.login_as_polls_user()
        self.add_credentials(user.role, all='!CHANGE')

        line1, line2, line3 = self.create_3_lines_4_conditions(user=user)

        PollFormLineCondition.objects.create(
            line=line3, source=line1, raw_answer='1',
            operator=PollFormLineCondition.EQUALS,
        )
        self.assertGET403(self.build_editlineconditions_url(line3))

    # TODO: remove conditions --> update conds_use_or ?? (or remove 'None' feature)

    def test_disable_line01(self):
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')
        line = PollFormLine.objects.create(
            pform=pform, type=PollLineType.INT,
            order=1, question='How old is this swallow ?'
        )
        self.assertFalse(line.disabled)

        url = self.build_disableline_url(line)
        self.assertGET404(url)  # Only POST
        self.assertRedirects(self.disable_line(line), pform.get_absolute_url())
        self.assertTrue(self.assertStillExists(line).disabled)

    def test_disable_line02(self):
        "Disabled line depends on other lines."
        user = self.login_as_root_and_get()
        line1, line2, line3 = self.create_3_lines_4_conditions(user=user)

        create_cond = partial(
            PollFormLineCondition.objects.create,
            line=line3, operator=PollFormLineCondition.EQUALS,
        )
        cond1 = create_cond(source=line1, raw_answer='1')
        cond2 = create_cond(source=line2, raw_answer='2')

        self.assertEqual(302, self.disable_line(line3).status_code)
        self.assertTrue(self.assertStillExists(line3).disabled)
        self.assertFalse(
            PollFormLineCondition.objects.filter(id__in=[cond1.id, cond2.id]).exists()
        )

    def test_disable_line03(self):
        "Disabled line has a line that depends on it."
        user = self.login_as_root_and_get()
        line2, line3 = self.create_3_lines_4_conditions(user=user)[1:]
        cond = PollFormLineCondition.objects.create(
            line=line3, source=line2, raw_answer='1',
            operator=PollFormLineCondition.EQUALS,
        )

        self.assertEqual(403, self.disable_line(line2).status_code)
        self.assertFalse(self.assertStillExists(line2).disabled)
        self.assertStillExists(cond)

        # TODO: when 404 rendering is improved
        # self.assertIn(
        #     _('There is at least one other question which depends on this question.'),
        #     response.content
        # )

    def test_disable_line04(self):
        "Already disabled."
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')
        line = PollFormLine.objects.create(
            pform=pform, type=PollLineType.INT,
            order=1, question='How old is this swallow ?',
            disabled=True,
        )
        self.assertEqual(403, self.disable_line(line).status_code)

    def test_disable_line_ajax01(self):
        "Disabled line depends on other lines."
        user = self.login_as_root_and_get()
        line1, line2, line3 = self.create_3_lines_4_conditions(user=user)

        create_cond = partial(
            PollFormLineCondition.objects.create,
            line=line3, operator=PollFormLineCondition.EQUALS,
        )
        cond1 = create_cond(source=line1, raw_answer='1')
        cond2 = create_cond(source=line2, raw_answer='2')

        self.assertEqual(200, self.disable_line(line3, ajax=True).status_code)
        self.assertTrue(self.assertStillExists(line3).disabled)
        self.assertDoesNotExist(cond1)
        self.assertDoesNotExist(cond2)

    def test_disable_line_ajax02(self):
        "Disabled line has a line that depends on it."
        user = self.login_as_root_and_get()
        line2, line3 = self.create_3_lines_4_conditions(user=user)[1:]
        cond = PollFormLineCondition.objects.create(
            line=line3, source=line2, raw_answer='1',
            operator=PollFormLineCondition.EQUALS,
        )

        response = self.disable_line(line2, ajax=True)
        self.assertEqual(403, response.status_code)
        self.assertFalse(self.assertStillExists(line2).disabled)
        self.assertStillExists(cond)
        self.assertEqual(
            _('There is at least one other question which depends on this question.'),
            response.text,
        )

    def test_delete_line01(self):
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')
        line = PollFormLine.objects.create(
            pform=pform, type=PollLineType.INT,
            order=1, question='How old is this swallow ?',
        )

        self.assertGET405(self.build_deleteline_url())  # Only POST
        self.assertRedirects(self.delete_line(line), pform.get_absolute_url())
        self.assertDoesNotExist(line)

    def test_delete_line02(self):
        "Deleted line depends on other lines."
        user = self.login_as_root_and_get()
        line1, line2, line3 = self.create_3_lines_4_conditions(user=user)

        create_cond = partial(
            PollFormLineCondition.objects.create,
            line=line3, operator=PollFormLineCondition.EQUALS,
        )
        cond1 = create_cond(source=line1, raw_answer='1')
        cond2 = create_cond(source=line2, raw_answer='2')

        self.assertEqual(302, self.delete_line(line3).status_code)
        self.assertDoesNotExist(line3)
        self.assertDoesNotExist(cond1)
        self.assertDoesNotExist(cond2)

    def test_delete_line03(self):
        "Deleted line has a line that depends on it."
        user = self.login_as_root_and_get()
        line2, line3 = self.create_3_lines_4_conditions(user=user)[1:]
        cond = PollFormLineCondition.objects.create(
            line=line3, source=line2, raw_answer='1',
            operator=PollFormLineCondition.EQUALS
        )

        response = self.delete_line(line2)
        self.assertEqual(409, response.status_code)
        self.assertStillExists(line2)
        self.assertStillExists(cond)

        # TODO: when 404 rendering is improved
        # self.assertIn(
        #     _('There is at least one other question which depends on this question.'),
        #     response.content
        # )

    # def test_delete_line04(self): #TODO ??
    #     pform = PollForm.objects.create(user=self.user, name='Form#1')
    #     line = PollFormLine.objects.create(pform=pform, type=PollLineType.INT,
    #                                        order=1, question='How old is this swallow ?',
    #                                        deleted=True
    #                                       )
    #     self.assertEqual(404, self._delete_line(line).status_code)

    def test_delete_line_ajax01(self):
        "Deleted line depends on other lines."
        user = self.login_as_root_and_get()
        line1, line2, line3 = self.create_3_lines_4_conditions(user=user)

        create_cond = partial(
            PollFormLineCondition.objects.create,
            line=line3, operator=PollFormLineCondition.EQUALS,
        )
        cond1 = create_cond(source=line1, raw_answer='1')
        cond2 = create_cond(source=line2, raw_answer='2')

        self.assertEqual(200, self.delete_line(line3, ajax=True).status_code)
        self.assertDoesNotExist(line3)
        self.assertDoesNotExist(cond1)
        self.assertDoesNotExist(cond2)

    def test_delete_line_ajax02(self):
        "Deleted line has a line that depends on it."
        user = self.login_as_root_and_get()
        line2, line3 = self.create_3_lines_4_conditions(user=user)[1:]
        cond = PollFormLineCondition.objects.create(
            line=line3, source=line2, raw_answer='1',
            operator=PollFormLineCondition.EQUALS,
        )

        response = self.delete_line(line2, ajax=True)
        self.assertEqual(409, response.status_code)
        self.assertStillExists(line2)
        self.assertStillExists(cond)
        self.assertHTMLEqual(
            '<span>{message}</span><ul><li>{dependencies}</li></ul>'.format(
                message=_(
                    'This deletion cannot be performed because of the links '
                    'with some entities (& other elements):'
                ),
                dependencies=_('{count} {model}').format(
                    count=1,
                    model=smart_model_verbose_name(model=PollFormLine, count=1),
                )
            ),
            response.text,
        )

    def test_get_choices01(self):
        "ENUM."
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')
        choices = [[1, 'White'], [2, 'Black'], [3, 'Green']]
        line = self._get_formline_creator(pform)(
            'What is your favorite color ?',
            qtype=PollLineType.ENUM, choices=choices,
        )

        response = self.assertGET200(self.build_choices_url(line))
        self.assertEqual(choices, response.json())

    def test_get_choices02(self):
        "MULTI_ENUM."
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
        response = self.assertGET200(self.build_choices_url(line))
        self.assertEqual(choices, response.json())

    def test_get_choices03(self):
        "ENUM_OR_STRING."
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')
        choices = [[1, 'Cat'], [2, 'Dog'], [3, 'Fish']]
        line = self._get_formline_creator(pform)(
            'What is your pet ?',
            qtype=PollLineType.ENUM_OR_STRING, choices=choices,
        )
        response = self.assertGET200(self.build_choices_url(line))
        self.assertListEqual([[0, _('Other')], *choices], response.json())

    def test_get_choices04(self):
        "BOOL."
        user = self.login_as_root_and_get()
        line = PollFormLine.objects.create(
            pform=PollForm.objects.create(user=user, name='Form#1'),
            question='Do you love swallows ?',
            order=1, type=PollLineType.BOOL,
        )
        response = self.assertGET200(self.build_choices_url(line))
        self.assertEqual([[0, _('No')], [1, _('Yes')]], response.json())

    def test_get_choices_error01(self):
        "Bad type."
        user = self.login_as_root_and_get()
        line = PollFormLine.objects.create(
            pform=PollForm.objects.create(user=user, name='Form#1'),
            question='What do you like ?',
            order=1, type=PollLineType.STRING,
        )
        self.assertGET404(self.build_choices_url(line))

    # TODO: use Nullable feature to avoid query
    def test_condition_getters01(self):
        user = self.login_as_root_and_get()
        line = PollFormLine.objects.create(
            pform=PollForm.objects.create(user=user, name='Form#1'),
            question='Do you love swallows ?',
            order=1, type=PollLineType.INT,
        )

        with self.assertNumQueries(1):  # TODO: 0
            conditions = line.get_conditions()
        self.assertListEqual([], conditions)

        with self.assertNumQueries(1):  # TODO: 0
            conditions = line.get_reversed_conditions()
        self.assertListEqual([], conditions)

    def test_condition_getters02(self):
        user = self.login_as_root_and_get()
        line1, line2, line3 = self.create_3_lines_4_conditions(user=user)
        line4 = PollFormLine.objects.create(
            pform=line1.pform, order=4, type=PollLineType.BOOL,
            question='Do you love green swallows ?',
        )

        create_cond = partial(
            PollFormLineCondition.objects.create,
            operator=PollFormLineCondition.EQUALS,
        )
        cond1 = create_cond(line=line3, source=line1, raw_answer='2')
        cond2 = create_cond(line=line3, source=line2, raw_answer='2')
        cond3 = create_cond(line=line4, source=line1, raw_answer='2')

        # TODO
        # line3.use_or = True; line3.save()
        # line4.use_or = True; line3.save()

        with self.assertNumQueries(1):  # TODO: 0
            conditions = line1.get_conditions()
        self.assertListEqual([], conditions)

        with self.assertNumQueries(1):  # TODO: 0
            conditions = line2.get_conditions()
        self.assertListEqual([], conditions)

        with self.assertNumQueries(1):
            conditions = line3.get_conditions()
        self.assertListEqual([cond1, cond2], conditions)

        with self.assertNumQueries(0):
            line3.get_conditions()

        with self.assertNumQueries(1):
            conditions = line1.get_reversed_conditions()
        self.assertListEqual([cond1, cond3], conditions)

        with self.assertNumQueries(0):
            line1.get_reversed_conditions()

    def test_condition_getters03(self):
        "Use populate_conditions()."
        user = self.login_as_root_and_get()
        line1, line2, line3 = self.create_3_lines_4_conditions(user=user)
        line4 = PollFormLine.objects.create(
            pform=line1.pform, order=4, type=PollLineType.BOOL,
            question='Do you love green swallows ?',
        )

        create_cond = partial(
            PollFormLineCondition.objects.create, operator=PollFormLineCondition.EQUALS,
        )
        cond1 = create_cond(line=line3, source=line1, raw_answer='2')
        cond2 = create_cond(line=line3, source=line2, raw_answer='2')
        cond3 = create_cond(line=line4, source=line1, raw_answer='2')

        # TODO
        # line3.use_or = True; line3.save()
        # line4.use_or = True; line3.save()

        with self.assertNumQueries(1):
            PollFormLine.populate_conditions([line1, line2, line3, line4])

        with self.assertNumQueries(0):
            conditions = line1.get_conditions()
        self.assertListEqual([], conditions)

        with self.assertNumQueries(0):
            conditions = line3.get_conditions()
        self.assertListEqual([cond1, cond2], conditions)

        with self.assertNumQueries(0):
            conditions = line1.get_reversed_conditions()
        self.assertListEqual([cond1, cond3], conditions)

    def test_poll_line_condition(self):
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')

        create_line = self._get_formline_creator(pform)
        line1 = create_line(
            'How do you like swallows ?',
            qtype=PollLineType.ENUM,
            choices=[[1, 'A little bit'], [2, 'A lot']],
        )
        line2 = create_line(
            'How do you like parrots ?',
            qtype=PollLineType.ENUM_OR_STRING,
            choices=[[1, 'A little bit'], [2, 'A lot']],
        )
        line3 = create_line(
            'What nuts do you like ?',
            qtype=PollLineType.MULTI_ENUM,
            choices=[[1, 'Coco nuts'], [2, 'Peanuts']],
        )

        line_with_conds = create_line(
            'Do you love all birds ?',
            qtype=PollLineType.STRING, order=6, conds_use_or=False,
        )

        create_cond = partial(
            PollFormLineCondition.objects.create, operator=PollFormLineCondition.EQUALS,
        )
        dumps = json_dump
        cond1 = create_cond(line=line_with_conds, source=line1, raw_answer='2')
        cond2 = create_cond(line=line_with_conds, source=line2, raw_answer=dumps([1]))
        cond3 = create_cond(line=line_with_conds, source=line2, raw_answer=dumps([0]))
        cond4 = create_cond(line=line_with_conds, source=line3, raw_answer=dumps([1]))

        nodes = SectionTree(pform)
        msg_fmt1 = _('The answer to the question #{number} is «{answer}».')
        msg_fmt2 = _('The answer to the question #{number} contains «{answer}».')
        self.assertEqual(
            msg_fmt1.format(number=1, answer='A lot'),
            poll_line_condition(nodes, cond1),
        )
        self.assertEqual(
            msg_fmt1.format(number=2, answer='A little bit'),
            poll_line_condition(nodes, cond2),
        )
        self.assertEqual(
            msg_fmt1.format(number=2, answer=_('Other')),
            poll_line_condition(nodes, cond3),
        )
        self.assertEqual(
            msg_fmt2.format(number=3, answer='Coco nuts'),
            poll_line_condition(nodes, cond4),
        )

        self.assertGET200(pform.get_absolute_url())

    def test_clone01(self):
        "Cloning a form with multiple sections, lines and conditions."
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')
        create_section = partial(PollFormSection.objects.create, pform=pform)
        create_line = self._get_formline_creator(pform)

        section      = create_section(name='Chapter I',   order=1)
        sub_section1 = create_section(name='Chapter I.1', order=2, parent=section)
        sub_section2 = create_section(name='Chapter I.2', order=3, parent=section)

        line1 = create_line(
            'How do you like swallows ?',
            qtype=PollLineType.ENUM,
            section=section, choices=[[1, 'A little bit'], [2, 'A lot']],
        )
        line2 = create_line(
            'How do you like parrots ?',
            qtype=PollLineType.ENUM_OR_STRING,
            section=sub_section1, choices=[[1, 'A little bit'], [2, 'A lot']],
        )
        line3 = create_line(
            'What nuts do you like ?',
            qtype=PollLineType.MULTI_ENUM,
            section=sub_section2, choices=[[1, 'Coco nuts'], [2, 'Peanuts']],
        )
        line_with_conds = create_line(
            'Do you love all birds ?', order=6, conds_use_or=False,
        )
        create_cond = partial(
            PollFormLineCondition.objects.create, operator=PollFormLineCondition.EQUALS,
        )
        dumps = json_dump
        create_cond(line=line_with_conds, source=line1, raw_answer='2')
        create_cond(line=line_with_conds, source=line2, raw_answer=dumps([1]))
        create_cond(line=line_with_conds, source=line2, raw_answer=dumps([0]))
        create_cond(line=line_with_conds, source=line3, raw_answer=dumps([1]))

        count_pforms = PollForm.objects.count()
        count_sections = PollFormSection.objects.count()
        count_lines = PollFormLine.objects.count()
        count_conditions = PollFormLineCondition.objects.count()

        cloned_pform = self.clone(pform)

        self.assertEqual(pform.name, cloned_pform.name)
        self.assertEqual(pform.type, cloned_pform.type)

        self.assertEqual(count_pforms + 1, PollForm.objects.count())
        self.assertEqual(count_sections + 3, PollFormSection.objects.count())
        self.assertEqual(count_lines + 4, PollFormLine.objects.count())
        self.assertEqual(count_conditions + 4, PollFormLineCondition.objects.count())

        nodes = [*SectionTree(pform)]
        cloned_nodes = [*SectionTree(cloned_pform)]
        self.assertEqual(len(nodes), len(cloned_nodes))

        line_attrs = ('order', 'type', 'type_args', 'conds_use_or', 'question')
        section_attrs = ('name', 'body', 'order')

        for node, cnode in zip(nodes, cloned_nodes):
            is_section = node.is_section
            self.assertEqual(is_section, cnode.is_section)

            for attr in (section_attrs if is_section else line_attrs):
                self.assertEqual(getattr(node, attr), getattr(cnode, attr))

    def test_clone02(self):
        "Disabled lines excluded when cloning a form."
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')
        count_pforms = PollForm.objects.count()

        create_line = self._get_formline_creator(pform)
        create_line(
            'How do you like swallows ?',
            qtype=PollLineType.ENUM,
            choices=[[1, 'A little bit'], [2, 'A lot']],
            disabled=True,  # <=======
        )
        create_line(
            'How do you like parrots ?',
            qtype=PollLineType.ENUM_OR_STRING,
            choices=[[1, 'A little bit'], [2, 'A lot']],
        )

        cloned_pform = self.clone(pform)
        self.assertEqual(pform.name, cloned_pform.name)
        self.assertEqual(pform.type, cloned_pform.type)

        self.assertEqual(count_pforms + 1, PollForm.objects.count())
        self.assertEqual(1, PollFormLine.objects.filter(pform__id=cloned_pform.id).count())

    # def test_clone__method01(self):  # DEPRECATED
    #     "Cloning a form with multiple sections, lines and conditions."
    #     user = self.login_as_root_and_get()
    #     pform = PollForm.objects.create(user=user, name='Form#1')
    #     create_section = partial(PollFormSection.objects.create, pform=pform)
    #     create_line = self._get_formline_creator(pform)
    #
    #     section      = create_section(name='Chapter I',   order=1)
    #     sub_section1 = create_section(name='Chapter I.1', order=2, parent=section)
    #     sub_section2 = create_section(name='Chapter I.2', order=3, parent=section)
    #
    #     line1 = create_line(
    #         'How do you like swallows ?',
    #         qtype=PollLineType.ENUM,
    #         section=section, choices=[[1, 'A little bit'], [2, 'A lot']],
    #     )
    #     line2 = create_line(
    #         'How do you like parrots ?',
    #         qtype=PollLineType.ENUM_OR_STRING,
    #         section=sub_section1, choices=[[1, 'A little bit'], [2, 'A lot']],
    #     )
    #     line3 = create_line(
    #         'What nuts do you like ?',
    #         qtype=PollLineType.MULTI_ENUM,
    #         section=sub_section2, choices=[[1, 'Coco nuts'], [2, 'Peanuts']],
    #     )
    #     line_with_conds = create_line(
    #         'Do you love all birds ?', order=6, conds_use_or=False,
    #     )
    #     create_cond = partial(
    #         PollFormLineCondition.objects.create, operator=PollFormLineCondition.EQUALS,
    #     )
    #     dumps = json_dump
    #     create_cond(line=line_with_conds, source=line1, raw_answer='2')
    #     create_cond(line=line_with_conds, source=line2, raw_answer=dumps([1]))
    #     create_cond(line=line_with_conds, source=line2, raw_answer=dumps([0]))
    #     create_cond(line=line_with_conds, source=line3, raw_answer=dumps([1]))
    #
    #     count_pforms = PollForm.objects.count()
    #     count_sections = PollFormSection.objects.count()
    #     count_lines = PollFormLine.objects.count()
    #     count_conditions = PollFormLineCondition.objects.count()
    #
    #     cloned_pform = pform.clone()
    #
    #     self.assertEqual(pform.name, cloned_pform.name)
    #     self.assertEqual(pform.type, cloned_pform.type)
    #
    #     self.assertEqual(count_pforms + 1, PollForm.objects.count())
    #     self.assertEqual(count_sections + 3, PollFormSection.objects.count())
    #     self.assertEqual(count_lines + 4, PollFormLine.objects.count())
    #     self.assertEqual(count_conditions + 4, PollFormLineCondition.objects.count())
    #
    #     nodes = [*SectionTree(pform)]
    #     cloned_nodes = [*SectionTree(cloned_pform)]
    #     self.assertEqual(len(nodes), len(cloned_nodes))
    #
    #     line_attrs = ('order', 'type', 'type_args', 'conds_use_or', 'question')
    #     section_attrs = ('name', 'body', 'order')
    #
    #     for node, cnode in zip(nodes, cloned_nodes):
    #         is_section = node.is_section
    #         self.assertEqual(is_section, cnode.is_section)
    #
    #         for attr in (section_attrs if is_section else line_attrs):
    #             self.assertEqual(getattr(node, attr), getattr(cnode, attr))
    #
    # def test_clone_method02(self):  # DEPRECATED
    #     "Disabled lines excluded when cloning a form."
    #     user = self.login_as_root_and_get()
    #     pform = PollForm.objects.create(user=user, name='Form#1')
    #     count_pforms = PollForm.objects.count()
    #
    #     create_line = self._get_formline_creator(pform)
    #     create_line(
    #         'How do you like swallows ?',
    #         qtype=PollLineType.ENUM,
    #         choices=[[1, 'A little bit'], [2, 'A lot']],
    #         disabled=True,  # <=======
    #     )
    #     create_line(
    #         'How do you like parrots ?',
    #         qtype=PollLineType.ENUM_OR_STRING,
    #         choices=[[1, 'A little bit'], [2, 'A lot']],
    #     )
    #
    #     cloned_pform = pform.clone()
    #     self.assertEqual(pform.name, cloned_pform.name)
    #     self.assertEqual(pform.type, cloned_pform.type)
    #
    #     self.assertEqual(count_pforms + 1, PollForm.objects.count())
    #     self.assertEqual(1, PollFormLine.objects.filter(pform__id=cloned_pform.id).count())

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
