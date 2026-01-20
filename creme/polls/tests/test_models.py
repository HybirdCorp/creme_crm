from functools import partial
from json import dumps as json_dump

from django.contrib.contenttypes.models import ContentType
from django.test.utils import override_settings
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.utils.translation import smart_model_verbose_name
from creme.polls.core import PollLineType
from creme.polls.models import (
    PollFormLine,
    PollFormLineCondition,
    PollFormSection,
    PollType,
)
from creme.polls.templatetags.polls_tags import poll_line_condition
from creme.polls.tests.base import (
    PollForm,
    _PollsTestCase,
    skipIfCustomPollForm,
)
from creme.polls.utils import SectionTree


@skipIfCustomPollForm
class PollFormTestCase(_PollsTestCase):
    # TODO: use Nullable feature to avoid query
    def test_condition_getters__empty(self):
        user = self.login_as_root_and_get()
        line = PollFormLine.objects.create(
            pform=PollForm.objects.create(user=user, name='Form#1'),
            question='Do you love swallows?',
            order=1, type=PollLineType.INT,
        )

        with self.assertNumQueries(1):  # TODO: 0
            conditions = line.get_conditions()
        self.assertListEqual([], conditions)

        with self.assertNumQueries(1):  # TODO: 0
            conditions = line.get_reversed_conditions()
        self.assertListEqual([], conditions)

    def test_condition_getters__filled(self):
        user = self.login_as_root_and_get()
        line1, line2, line3 = self._create_pform_with_3_lines_for_conditions(user=user)
        line4 = PollFormLine.objects.create(
            pform=line1.pform, order=4, type=PollLineType.BOOL,
            question='Do you love green swallows?',
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

    def test_condition_getters__populate(self):
        "Use populate_conditions()."
        user = self.login_as_root_and_get()
        line1, line2, line3 = self._create_pform_with_3_lines_for_conditions(user=user)
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

    @override_settings(ENTITIES_DELETION_ALLOWED=True)
    def test_deletion(self):
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
    def test_deletion__cascade(self):
        user = self.login_as_root_and_get()
        line1, line2, line3 = self._create_pform_with_3_lines_for_conditions(user=user)
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

    def test_type_deletion(self):
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

    def test_cloning(self):
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

    def test_cloning__disabled_lines(self):
        "Disabled lines excluded when cloning a form."
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')
        count_pforms = PollForm.objects.count()

        create_line = self._get_formline_creator(pform)
        create_line(
            'How do you like swallows?',
            qtype=PollLineType.ENUM,
            choices=[[1, 'A little bit'], [2, 'A lot']],
            disabled=True,  # <=======
        )
        create_line(
            'How do you like parrots?',
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

    def test_line_condition(self):
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')

        create_line = self._get_formline_creator(pform)
        line1 = create_line(
            'How do you like swallows?',
            qtype=PollLineType.ENUM,
            choices=[[1, 'A little bit'], [2, 'A lot']],
        )
        line2 = create_line(
            'How do you like parrots?',
            qtype=PollLineType.ENUM_OR_STRING,
            choices=[[1, 'A little bit'], [2, 'A lot']],
        )
        line3 = create_line(
            'What nuts do you like?',
            qtype=PollLineType.MULTI_ENUM,
            choices=[[1, 'Coco nuts'], [2, 'Peanuts']],
        )

        line_with_conds = create_line(
            'Do you love all birds?',
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

        # TODO: complete + move this part in views tests
        self.assertGET200(pform.get_absolute_url())


class PollFormSectionTestCase(_PollsTestCase):
    @staticmethod
    def _build_deletion_url():
        return reverse(
            'creme_core__delete_related_to_entity',
            args=(ContentType.objects.get_for_model(PollFormSection).id,),
        )

    def _delete(self, section, ajax=False):
        kwargs = {} if not ajax else {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}

        return self.client.post(
            self._build_deletion_url(), data={'id': section.id}, **kwargs
        )

    def test_delete(self):
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')
        section = PollFormSection.objects.create(pform=pform, name='Introduction', order=1)

        self.assertGET405(self._build_deletion_url())

        self.assertEqual([False], [node.has_line for node in SectionTree(pform)])

        self.assertEqual(200, self._delete(section, ajax=True).status_code)
        self.assertDoesNotExist(section)

    def test_delete__with_a_line(self):
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

        self.assertEqual(409, self._delete(section).status_code)
        self.assertStillExists(line)
        self.assertStillExists(section)

        # TODO: when 404 rendering is improved
        # self.assertIn(_('There is at least one question in this section.'), response.content)

    def test_delete__sub_section__empty(self):
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

        self.assertRedirects(self._delete(section), pform.get_absolute_url())
        self.assertFalse(PollFormSection.objects.filter(pk__in=[section.pk, sub_section.pk]))

    def test_delete__sub_section__not_empty(self):
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

        response = self._delete(section, ajax=True)
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


class PollFormLineTestCase(_PollsTestCase):
    @staticmethod
    def _build_deletion_url():
        return reverse(
            'creme_core__delete_related_to_entity',
            args=(ContentType.objects.get_for_model(PollFormLine).id,),
        )

    def _delete(self, line, ajax=False):
        kwargs = {} if not ajax else {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}

        return self.client.post(self._build_deletion_url(), data={'id': line.id}, **kwargs)

    def test_delete(self):
        user = self.login_as_root_and_get()
        pform = PollForm.objects.create(user=user, name='Form#1')
        line = PollFormLine.objects.create(
            pform=pform, type=PollLineType.INT,
            order=1, question='How old is this swallow?',
        )

        self.assertGET405(self._build_deletion_url())  # Only POST
        self.assertRedirects(self._delete(line), pform.get_absolute_url())
        self.assertDoesNotExist(line)

    def test_delete__is_destination(self):
        "Deleted line depends on other lines."
        user = self.login_as_root_and_get()
        line1, line2, line3 = self._create_pform_with_3_lines_for_conditions(user=user)

        create_cond = partial(
            PollFormLineCondition.objects.create,
            line=line3, operator=PollFormLineCondition.EQUALS,
        )
        cond1 = create_cond(source=line1, raw_answer='1')
        cond2 = create_cond(source=line2, raw_answer='2')

        self.assertEqual(302, self._delete(line3).status_code)
        self.assertDoesNotExist(line3)
        self.assertDoesNotExist(cond1)
        self.assertDoesNotExist(cond2)

    def test_delete__is_source(self):
        "Deleted line has a line that depends on it."
        user = self.login_as_root_and_get()
        line2, line3 = self._create_pform_with_3_lines_for_conditions(user=user)[1:]
        cond = PollFormLineCondition.objects.create(
            line=line3, source=line2, raw_answer='1',
            operator=PollFormLineCondition.EQUALS
        )

        response = self._delete(line2)
        self.assertEqual(409, response.status_code)
        self.assertStillExists(line2)
        self.assertStillExists(cond)

        # TODO: when 404 rendering is improved
        # self.assertIn(
        #     _('There is at least one other question which depends on this question.'),
        #     response.content
        # )

    # def test_delete_...(self): #TODO ??
    #     pform = PollForm.objects.create(user=self.user, name='Form#1')
    #     line = PollFormLine.objects.create(pform=pform, type=PollLineType.INT,
    #                                        order=1, question='How old is this swallow?',
    #                                        deleted=True,
    #                                       )
    #     self.assertEqual(404, self._delete_line(line).status_code)

    def test_delete__ajax__is_destination(self):
        "Deleted line depends on other lines."
        user = self.login_as_root_and_get()
        line1, line2, line3 = self._create_pform_with_3_lines_for_conditions(user=user)

        create_cond = partial(
            PollFormLineCondition.objects.create,
            line=line3, operator=PollFormLineCondition.EQUALS,
        )
        cond1 = create_cond(source=line1, raw_answer='1')
        cond2 = create_cond(source=line2, raw_answer='2')

        self.assertEqual(200, self._delete(line3, ajax=True).status_code)
        self.assertDoesNotExist(line3)
        self.assertDoesNotExist(cond1)
        self.assertDoesNotExist(cond2)

    def test_delete__ajax__is_source(self):
        "Deleted line has a line that depends on it."
        user = self.login_as_root_and_get()
        line2, line3 = self._create_pform_with_3_lines_for_conditions(user=user)[1:]
        cond = PollFormLineCondition.objects.create(
            line=line3, source=line2, raw_answer='1',
            operator=PollFormLineCondition.EQUALS,
        )

        response = self._delete(line2, ajax=True)
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


class PollReplyTestCase(_PollsTestCase):
    def test_delete_type(self):
        "Set to NULL."
        user = self.login_as_root_and_get()
        ptype  = PollType.objects.create(name='Political poll')
        preply = self._create_preply(user=user, ptype=ptype)

        self.assertNoFormError(self.client.post(
            reverse(
                'creme_config__delete_instance',
                args=('polls', 'poll_type', ptype.id),
            ),
        ))

        job = self.get_deletion_command_or_fail(PollType).job
        job.type.execute(job)
        self.assertDoesNotExist(ptype)

        preply = self.assertStillExists(preply)
        self.assertIsNone(preply.type)
