# -*- coding: utf-8 -*-

from datetime import date
from functools import partial
from json import dumps as dump_json
from json import loads as load_json

from django.forms.widgets import Select
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.activities import get_activity_model
from creme.activities.models import ActivityType
from creme.activities.tests.base import skipIfCustomActivity
from creme.creme_core.auth import EntityCredentials
from creme.creme_core.forms.widgets import UnorderedMultipleChoiceWidget
from creme.creme_core.models import SetCredentials
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.persons import get_contact_model, get_organisation_model
from creme.persons.tests.base import (
    skipIfCustomContact,
    skipIfCustomOrganisation,
)

from ..bricks import PollReplyLinesBrick
from ..core import PollLineType
from ..models import (
    PollFormLine,
    PollFormLineCondition,
    PollFormSection,
    PollReplyLine,
    PollReplyLineCondition,
    PollReplySection,
    PollType,
)
from ..utils import SectionTree, StatsTree
from .base import (
    PollCampaign,
    PollForm,
    PollReply,
    _PollsTestCase,
    skipIfCustomPollCampaign,
    skipIfCustomPollForm,
    skipIfCustomPollReply,
)

Contact = get_contact_model()
Organisation = get_organisation_model()
Activity = get_activity_model()


@skipIfCustomPollForm
@skipIfCustomPollReply
class PollRepliesTestCase(_PollsTestCase, BrickTestCaseMixin):
    def assertCurrentQuestion(self, response, fline, line_number=None):
        try:
            question_f = response.context['form'].fields['question']
        except KeyError as e:
            self.fail(
                f'It seems that the form is already complete'
                f' (<{e.__class__.__name__}> occurred: {e})'
            )

        self.assertEqual(
            f'{line_number or fline.order} - {fline.question}',
            question_f.initial,
        )

    def assertPollLinesEqual(self, line1, line2):
        self.assertEqual(line1.question, line2.question)
        self.assertEqual(line1.order,    line2.order)

        self.assertEqual(line1.type,                     line2.type)
        self.assertEqual(line1.type_args,                line2.type_args)
        self.assertEqual(line1.poll_line_type.__class__, line2.poll_line_type.__class__)

        self.assertEqual(line1.conds_use_or, line2.conds_use_or)
        # Beware: source are not compared (would need a pk translation)
        self.assertListEqual(
            [*line1.conditions.values('operator', 'raw_answer')],
            [*line2.conditions.values('operator', 'raw_answer')]
        )

    @staticmethod
    def _build_linkto_url(entity):
        return reverse('polls__link_reply_to_person', args=(entity.id,))

    @staticmethod
    def _build_preply_from_person_url(person):
        return reverse('polls__create_reply_from_person', args=(person.id,))

    def _build_reply_with_bool_line(self):
        return self._build_reply_with_1_line(PollLineType.BOOL, 'Do you like spam?')

    def _build_reply_with_enumorstring_line(self):
        return self._build_reply_with_1_line(
            PollLineType.ENUM_OR_STRING,
            'What is the main color of a swallow?',
            choices=[[1, 'White'], [2, 'Black'], [3, 'Green']],
        )

    def _build_reply_with_int_line(self, lower_bound=None, upper_bound=None):
        return self._build_reply_with_1_line(
            PollLineType.INT, 'How many swallows are there?',
            lower_bound=lower_bound, upper_bound=upper_bound,
        )

    def _build_reply_with_1_line(self, qtype, question, **type_kwargs):
        pform  = PollForm.objects.create(user=self.user, name='Form#1')
        fline = self._get_formline_creator(pform)(question, qtype=qtype, **type_kwargs)
        preply = self._build_preply_from_pform(pform, 'Reply#1')
        rline  = PollReplyLine.objects.get(pform_line=fline)

        return preply, rline

    def _build_reply_with_text_line(self):
        return self._build_reply_with_1_line(
            PollLineType.TEXT,
            'What is the difference between a swallow (argue)?',
        )

    def _build_reply_with_2_lines(self):
        pform = PollForm.objects.create(user=self.user, name='Form#1')

        create_line = self._get_formline_creator(pform)
        fline1 = create_line('How many swallows are there?', qtype=PollLineType.INT)
        fline2 = create_line("What is your swallow's name?", qtype=PollLineType.STRING)

        preply = self._build_preply_from_pform(pform, 'Reply#1')
        self.assertIs(preply.is_complete, False)

        get_rline = PollReplyLine.objects.get
        rline1  = get_rline(pform_line=fline1)
        rline2  = get_rline(pform_line=fline2)

        return preply, rline1, rline2

    def _build_rlines_with_condition(self, only_2_questions=False):
        pform  = PollForm.objects.create(user=self.user, name='Form#1')

        create_line = self._get_formline_creator(pform)
        fline1 = create_line(
            'How do you like swallows?',
            qtype=PollLineType.ENUM,
            choices=[[1, 'A little'], [2, 'A lot']],
        )
        self.fline2 = create_line('What type of swallow do you prefer?', conds_use_or=True)

        if not only_2_questions:
            self.fline3 = create_line('Do you eat swallows?')

        PollFormLineCondition.objects.create(
            line=self.fline2, source=fline1, raw_answer='2',
            operator=PollFormLineCondition.EQUALS,
        )

        self.preply = self._build_preply_from_pform(pform, 'Reply#1')
        self.rline1 = self.get_object_or_fail(PollReplyLine, pform_line=fline1)
        self.rline2 = rline2 = self.get_object_or_fail(PollReplyLine, pform_line=self.fline2)

        if not only_2_questions:
            self.get_object_or_fail(PollReplyLine, pform_line=self.fline3)

        self.rcondition = self.get_object_or_fail(PollReplyLineCondition, line=rline2)

    def _build_rlines_with_conditions(self, conds_use_or=False):
        pform  = PollForm.objects.create(user=self.user, name='Form#1')

        ENUM = PollLineType.ENUM
        create_line = self._get_formline_creator(pform)
        choices = [[1, 'A little'], [2, 'A lot']]
        fline1      = create_line('How do you like swallows?', qtype=ENUM, choices=choices)
        self.fline2 = create_line('How do you like parrots?',  qtype=ENUM, choices=choices)
        self.fline3 = create_line('Do you love all birds?', conds_use_or=conds_use_or)

        create_cond = partial(
            PollFormLineCondition.objects.create, operator=PollFormLineCondition.EQUALS,
        )
        create_cond(line=self.fline3, source=fline1,      raw_answer='2')
        create_cond(line=self.fline3, source=self.fline2, raw_answer='2')

        self.preply = self._build_preply_from_pform(pform, 'Reply#1')
        self.get_object_or_fail(PollReplyLine, pform_line=fline1)
        self.get_object_or_fail(PollReplyLine, pform_line=self.fline2)
        self.get_object_or_fail(PollReplyLine, pform_line=self.fline3)

    def _build_rlines_with_conditions_on_bool(self):
        pform  = PollForm.objects.create(user=self.user, name='Form#1')

        create_line = self._get_formline_creator(pform)
        fline1      = create_line('Do you like swallows?', qtype=PollLineType.BOOL)
        self.fline2 = create_line('Talk about them',        qtype=PollLineType.STRING)

        PollFormLineCondition.objects.create(
            line=self.fline2, source=fline1,
            raw_answer='1',
            operator=PollFormLineCondition.EQUALS
        )

        self.preply = self._build_preply_from_pform(pform, 'Reply#1')
        self.rline1 = self.get_object_or_fail(PollReplyLine, pform_line=fline1)
        self.rline2 = self.get_object_or_fail(PollReplyLine, pform_line=self.fline2)
        self.rcondition = self.get_object_or_fail(PollReplyLineCondition, line=self.rline2)

    def _build_rlines_with_conditions_on_enumorstring(self, raw_cond):
        pform = PollForm.objects.create(user=self.user, name='Form#1')

        create_line = self._get_formline_creator(pform)
        fline1 = create_line(
            'What nuts do you like?',
            qtype=PollLineType.ENUM_OR_STRING,
            choices=[[1, 'Coco nuts'], [2, 'Peanuts']]
        )
        self.fline2 = create_line('Talk about them')

        PollFormLineCondition.objects.create(
            line=self.fline2, source=fline1,
            raw_answer=dump_json([raw_cond]),
            operator=PollFormLineCondition.EQUALS,
        )

        self.preply = self._build_preply_from_pform(pform, 'Reply#1')
        self.rline1 = self.get_object_or_fail(PollReplyLine, pform_line=fline1)
        self.rline2 = self.get_object_or_fail(PollReplyLine, pform_line=self.fline2)
        self.rcondition = self.get_object_or_fail(PollReplyLineCondition, line=self.rline2)

    def _build_rlines_with_conditions_on_multienum(self):
        pform  = PollForm.objects.create(user=self.user, name='Form#1')

        create_line = self._get_formline_creator(pform)
        fline1 = create_line(
            'What nuts do you like?', qtype=PollLineType.MULTI_ENUM,
            choices=[[1, 'Coco nuts'], [2, 'Peanuts'], [3, 'Pistachio'], [4, 'Almonds']]
        )
        self.fline2 = create_line('Talk about them')

        PollFormLineCondition.objects.create(
            line=self.fline2, source=fline1,
            raw_answer=dump_json([1]),
            operator=PollFormLineCondition.EQUALS,
        )

        self.preply = self._build_preply_from_pform(pform, 'Reply#1')
        self.rline1 = self.get_object_or_fail(PollReplyLine, pform_line=fline1)
        self.rline2 = self.get_object_or_fail(PollReplyLine, pform_line=self.fline2)
        self.rcondition = self.get_object_or_fail(PollReplyLineCondition, line=self.rline2)

    @staticmethod
    def _build_edit_answer_url(preply, preply_line):
        return reverse('polls__edit_reply_line', args=(preply.id, preply_line.id))

    @staticmethod
    def _build_edit_wizard_answer_url(preply, line):
        return reverse('polls__edit_reply_line_wizard', args=(preply.id, line.id))

    @staticmethod
    def _build_fill_url(preply):
        return reverse('polls__fill_reply', args=(preply.id,))

    def _build_preply(self, ptype=None):
        user  = self.user
        pform = PollForm.objects.create(user=user, name='Form#1', type=ptype)
        return PollReply.objects.create(user=user, pform=pform, name='Reply#1', type=ptype)

    @staticmethod
    def _build_preply_from_pform_url(pform):
        return reverse('polls__create_reply_from_pform', args=(pform.id,))

    def _build_preply_from_pform(self, pform, name='Reply#1'):
        self.assertNoFormError(self.client.post(
            self._build_preply_from_pform_url(pform),
            data={
                'user': self.user.id,
                'name': name,
            },
        ))

        return self.get_object_or_fail(PollReply, name=name)

    def _create_activity(self):
        atype = ActivityType.objects.create(
            pk='polls-test-actype', name="Queen's blade",
            default_day_duration=7, default_hour_duration="00:00:00",
            is_custom=True,
        )
        return Activity.objects.create(user=self.user, type=atype)

    def _edit_answer(self, preply, rline, answer, is_complete):
        self.assertPOST200(
            self._build_edit_answer_url(preply, rline),
            data={'answer': answer},
        )
        self.assertEqual(answer, load_json(self.refresh(rline).raw_answer))
        self.assertEqual(is_complete, self.refresh(preply).is_complete)

    def _edit_wizard_answer(self, preply, rline, answer, is_complete):
        self.assertPOST200(
            self._build_edit_wizard_answer_url(preply, rline),
            data={'answer': answer}, follow=True,
        )
        self.assertEqual(answer, load_json(self.refresh(rline).raw_answer))
        self.assertEqual(is_complete, self.refresh(preply).is_complete)

    def _fill(self, preply, *answers, **kwargs):
        assert answers, 'Give at least one answer dude'
        url = self._build_fill_url(preply)
        response = None
        check_errors = kwargs.get('check_errors', True)
        not_applicable = kwargs.get('not_applicable', False)

        for answer in answers:
            data = {**answer} if isinstance(answer, dict) else {'answer': answer}

            if not_applicable:
                data['not_applicable'] = 'on'

            response = self.assertPOST200(url, follow=True, data=data)

            if check_errors:
                self.assertNoFormError(response)

        return response

    def test_createview01(self):
        user = self.login()
        self.assertFalse(PollReply.objects.all())

        pform = PollForm.objects.create(
            user=user, name='Form#1', type=PollType.objects.all()[0],
        )

        body = 'Blablabla'
        create_section = partial(PollFormSection.objects.create, pform=pform)
        section1  = create_section(name='1',  order=1, body=body)
        section11 = create_section(name='11', order=2, parent=section1)

        create_l = self._get_formline_creator(pform)
        fline1 = create_l(
            'What is the difference between a swallow?', qtype=PollLineType.INT,
        )
        fline2 = create_l('What type of swallow?', section1)
        fline3 = create_l(
            'How do you like swallows?', section11,
            qtype=PollLineType.ENUM,
            choices=[[1, 'A little'], [2, 'A lot'], [3, 'Passionately']],
        )
        fline4 = create_l('Do you eat swallows?', section11, conds_use_or=True)

        PollFormLineCondition.objects.create(
            line=fline4, source=fline3,
            raw_answer='1', operator=PollFormLineCondition.EQUALS,
        )

        url = self.ADD_REPLY_URL
        response = self.assertGET200(url)
        context = response.context
        self.assertEqual(_('Create replies'),   context.get('title'))
        self.assertEqual(_('Save the replies'), context.get('submit_label'))

        name = 'Reply#1'
        response = self.client.post(
            url,
            follow=True,
            data={
                'user':  user.id,
                'name':  name,
                'pform': pform.id,
            },
        )
        self.assertNoFormError(response)

        preply = self.get_object_or_fail(PollReply, name=name)
        self.assertEqual(user,       preply.user)
        self.assertEqual(pform,      preply.pform)
        self.assertEqual(pform.type, preply.type)
        self.assertEqual(2,          preply.sections.count())
        self.assertIsNone(preply.campaign)

        lines = preply.lines.all()
        self.assertEqual(4, len(lines))

        line_ids = [line.id for line in lines]
        self.assertEqual(sorted(line_ids), line_ids)

        self.assertRedirects(response, preply.get_absolute_url())

        # ----------------------------------------------------------------------
        line1 = lines[0]
        self.assertIsInstance(line1, PollReplyLine)
        self.assertPollLinesEqual(fline1, line1)
        self.assertIsNone(line1.section)
        self.assertIs(line1.applicable, True)

        # ----------------------------------------------------------------------
        line2 = lines[1]
        self.assertPollLinesEqual(fline2, line2)

        reply_section2 = line2.section
        self.assertIsInstance(reply_section2, PollReplySection)
        self.assertEqual(section1.name,  reply_section2.name)
        self.assertEqual(section1.body,  reply_section2.body)
        self.assertEqual(section1.order, reply_section2.order)
        self.assertEqual(preply,         reply_section2.preply)
        self.assertIsNone(reply_section2.parent)

        # ----------------------------------------------------------------------
        line3 = lines[2]
        self.assertPollLinesEqual(fline3, line3)

        reply_section3 = line3.section
        self.assertIsInstance(reply_section3, PollReplySection)
        self.assertEqual(section11.name,  reply_section3.name)
        self.assertEqual(section11.body,  reply_section3.body)
        self.assertEqual(section11.order, reply_section3.order)
        self.assertEqual(reply_section2,  reply_section3.parent)

        # ----------------------------------------------------------------------
        line4 = lines[3]
        self.assertPollLinesEqual(fline4, line4)
        self.assertEqual(line3, line4.conditions.all()[0].source)

        # ----------------------------------------------------------------------
        response = self.assertGET200(preply.get_absolute_url())
        brick_node = self.get_brick_node(
            self.get_html_tree(response.content), PollReplyLinesBrick.id_,
        )

        questions = set()
        for question_node in brick_node.findall(".//div[@class='poll-title-label']"):
            span_node = question_node.find('span')
            self.assertIsNotNone(span_node)
            questions.add(span_node.text)

        self.assertIn(line1.question, questions)
        self.assertIn(line2.question, questions)

    def test_createview02(self):
        "Create view: validation error when no PollForm"
        user = self.login()
        response = self.assertPOST200(
            self.ADD_REPLY_URL,
            follow=True,
            data={
                'user': user.id,
                'name': 'Reply#1',
            },
        )
        self.assertFormError(response, 'form', 'pform', _('This field is required.'))

    def test_createview03(self):
        "Create view: validation error when no line."
        user = self.login()
        pform = PollForm.objects.create(user=user, name='Form#1')

        response = self.assertPOST200(
            self.ADD_REPLY_URL,
            follow=True,
            data={
                'user':  user.id,
                'name':  'Reply#1',
                'pform': pform.id,
            },
        )
        self.assertFormError(
            response, 'form', 'pform',
            _('The form must contain one line at least.'),
        )

    def test_createview04(self):
        "Create view: validation error when no valid line."
        user = self.login()
        pform = PollForm.objects.create(user=user, name='Form#1')

        PollFormLine.objects.create(
            pform=pform, type=PollLineType.STRING, order=1,
            question='What is the difference between a swallow?',
            disabled=True,  # <=========
        )

        response = self.assertPOST200(
            self.ADD_REPLY_URL,
            follow=True,
            data={
                'user':  user.id,
                'name':  'Reply#1',
                'pform': pform.id,
            },
        )
        self.assertFormError(
            response, 'form', 'pform',
            _('The form must contain one line at least.'),
        )

    def test_createview05(self):
        "Create view: orders are not successive"
        user = self.login()
        pform = PollForm.objects.create(
            user=user, name='Form#1', type=PollType.objects.all()[0],
        )

        create_line = partial(
            PollFormLine.objects.create, pform=pform, type=PollLineType.STRING,
        )
        # The 1rst line is not 1 !
        create_line(question='What is the name of your swallow?', order=2)
        create_line(question='What type of swallow is it?',       order=5)
        create_line(question='What is its favorite nut?',         order=7)

        name = 'Reply#1'
        response = self.client.post(
            self.ADD_REPLY_URL,
            follow=True,
            data={
                'user':  user.id,
                'name':  name,
                'pform': pform.id,
            },
        )
        self.assertNoFormError(response)

        preply = self.get_object_or_fail(PollReply, name=name)
        self.assertFalse(preply.is_complete)
        self.assertEqual([1, 2, 3], [*preply.lines.values_list('order', flat=True)])

        # ---
        response = self.assertGET200(preply.get_absolute_url())
        self.assertTemplateUsed(response, 'polls/view_pollreply.html')

    def test_createview06(self):
        "Create view : create several replies"
        user = self.login()
        pform = PollForm.objects.create(user=user, name='Form#1')

        create_line = self._get_formline_creator(pform)
        create_line('What is the name of your swallow?')
        create_line('What type of swallow is it?')
        create_line('What is its favorite nut?')

        name = 'Reply'
        reply_number = 5
        response = self.client.post(
            self.ADD_REPLY_URL,
            follow=True,
            data={
                'user':   user.id,
                'name':   name,
                'pform':  pform.id,
                'number': reply_number,
            },
        )
        self.assertNoFormError(response)

        for i in range(1, reply_number + 1):
            preply = self.get_object_or_fail(PollReply, name='{}#{}'.format(name, i))
            self.assertFalse(preply.is_complete)
            self.assertListEqual(
                [1, 2, 3], [*preply.lines.values_list('order', flat=True)],
            )

    @skipIfCustomContact
    @skipIfCustomOrganisation
    def test_createview07(self):
        "Create view : create several replies linked to Contact/Organisation."
        user = self.login()
        count = PollReply.objects.count()

        pform = PollForm.objects.create(user=user, name='Form#1')

        create_line = self._get_formline_creator(pform)
        create_line('What is the name of your blade?')
        create_line('What type of blade is it?')

        create_contact = partial(Contact.objects.create, user=user)
        leina     = create_contact(first_name='Leina',     last_name='Vance')
        claudette = create_contact(first_name='Claudette', last_name='Vance')

        create_orga = partial(Organisation.objects.create, user=user)
        gaimos = create_orga(name='Gaimos')
        amara  = create_orga(name='Amara')

        name = 'FReply'
        response = self.client.post(
            self.ADD_REPLY_URL, follow=True,
            data={
                'user':    user.id,
                'name':    name,
                'pform':   pform.id,
                'number':  3,  # Should be ignored
                'persons': self.formfield_value_multi_generic_entity(
                    leina, claudette, gaimos, amara,
                ),
            },
        )
        self.assertNoFormError(response)

        self.assertEqual(count + 4, PollReply.objects.count())

        for i, entity in enumerate([leina, claudette, gaimos, amara], start=1):
            preply = self.get_object_or_fail(PollReply, name=f'{name}#{i}')
            self.assertEqual(entity, preply.person.get_real_entity())

    def test_create_from_pollform01(self):
        user = self.login()
        pform = PollForm.objects.create(user=user, name='Form#1')

        create_line = self._get_formline_creator(pform)
        create_line('Do you like swallows?')
        create_line('What type of swallow?')

        url = self._build_preply_from_pform_url(pform)
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/add-popup.html')

        context = response.context
        self.assertEqual(
            _('New replies for «{entity}»').format(entity=pform),
            context.get('title'),
        )
        self.assertEqual(PollReply.multi_save_label, context.get('submit_label'))

        name = 'Reply#1'
        self.assertNoFormError(self.client.post(
            url, data={'user': user.id, 'name': name},
        ))

        preply = self.get_object_or_fail(PollReply, name=name)
        self.assertEqual(pform, preply.pform)
        self.assertEqual(2,     preply.lines.count())

    def test_create_from_pollform02(self):
        "Create from PollForm: no lines causes a 404 error"
        user = self.login()
        pform = PollForm.objects.create(user=user, name='Form#1')
        self.assertGET404(self._build_preply_from_pform_url(pform))

    def test_create_from_pollform03(self):
        "Create from PollForm: no _valid_ lines causes a 404 error"
        user = self.login()
        pform = PollForm.objects.create(user=user, name='Form#1')
        self._get_formline_creator(pform)(
            'What is the difference between a swallow?',
            qtype=PollLineType.STRING,
            disabled=True,  # <=========
        )
        self.assertGET404(self._build_preply_from_pform_url(pform))

    def test_create_from_pollform04(self):
        "Create from PollForm: disabled lines are not copied"
        user = self.login()
        pform = PollForm.objects.create(user=user, name='Form#1')

        create_line = self._get_formline_creator(pform)
        lines = [
            create_line('Do you like swallows?', disabled=True),
            create_line('Do you love swallows?'),
        ]

        preply = self._build_preply_from_pform(pform)
        self.assertListEqual(
            [lines[1].question],
            [line.question for line in preply.lines.all()],
        )

    def test_create_from_pollform05(self):
        "Create from PollForm: deleted choices are not copied"
        user = self.login()
        pform = PollForm.objects.create(user=user, name='Form#1')
        choices = [[1, 'White'], [2, 'black']]
        line = self._get_formline_creator(pform)(
            'What are your favorite colors?',
            qtype=PollLineType.ENUM,
            choices=choices,
            del_choices=[[3, 'Red']],
        )
        preply = self._build_preply_from_pform(pform)

        with self.assertNoException():
            line = preply.lines.get(question=line.question)
            plt = line.poll_line_type
            del_choices = plt.get_deleted_choices()

        self.assertEqual(choices, plt.get_choices())
        self.assertFalse(del_choices)

    def test_create_from_pollform06(self):
        "Create from PollForm: several replies"
        user = self.login()
        pform = PollForm.objects.create(user=user, name='Form#1')

        create_line = self._get_formline_creator(pform)
        create_line('Do you like swallows?')
        create_line('What type of swallow?')

        name = 'Reply'
        reply_number = 5
        response = self.client.post(
            self._build_preply_from_pform_url(pform),
            data={
                'user':   user.id,
                'name':   name,
                'number': reply_number,
            },
        )
        self.assertNoFormError(response)

        for i in range(1, reply_number + 1):
            preply = self.get_object_or_fail(PollReply, name=f'{name}#{i}')
            self.assertEqual(pform, preply.pform)
            self.assertEqual(2,     preply.lines.count())

    def test_create_from_pollform07(self):
        "Not superuser."
        user = self.login(
            is_superuser=False, allowed_apps=['polls'], creatable_models=[PollReply],
        )
        SetCredentials.objects.create(
            role=self.role,
            value=(
                EntityCredentials.VIEW
                | EntityCredentials.CHANGE
                | EntityCredentials.DELETE
                | EntityCredentials.LINK
                | EntityCredentials.UNLINK
            ),
            set_type=SetCredentials.ESET_ALL,
        )

        pform = PollForm.objects.create(user=user, name='Form#1')

        create_line = self._get_formline_creator(pform)
        create_line('Do you like swallows?')

        self.assertGET200(self._build_preply_from_pform_url(pform))

    def test_create_from_pollform08(self):
        "Creation creds are needed"
        user = self.login(
            is_superuser=False, allowed_apps=['polls'],
            # creatable_models=[PollReply],
        )
        SetCredentials.objects.create(
            role=self.role,
            value=(
                EntityCredentials.VIEW
                | EntityCredentials.CHANGE
                | EntityCredentials.DELETE
                | EntityCredentials.LINK
                | EntityCredentials.UNLINK
            ),
            set_type=SetCredentials.ESET_ALL,
        )

        pform = PollForm.objects.create(user=user, name='Form#1')

        create_line = self._get_formline_creator(pform)
        create_line('Do you like swallows?')

        self.assertGET403(self._build_preply_from_pform_url(pform))

    def test_create_from_pollform09(self):
        "LINK creds are needed."
        user = self.login(
            is_superuser=False, allowed_apps=['polls'], creatable_models=[PollReply],
        )
        SetCredentials.objects.create(
            role=self.role,
            value=(
                EntityCredentials.VIEW
                | EntityCredentials.CHANGE
                | EntityCredentials.DELETE
                | EntityCredentials.UNLINK
                # | EntityCredentials.LINK
            ),
            set_type=SetCredentials.ESET_ALL,
        )

        pform = PollForm.objects.create(user=user, name='Form#1')

        create_line = self._get_formline_creator(pform)
        create_line('Do you like swallows?')

        self.assertGET403(self._build_preply_from_pform_url(pform))

    def _aux_test_link_to(self, person):
        user = self.user
        pform = PollForm.objects.create(user=user, name='Form#1')

        create_preply = partial(PollReply.objects.create, user=user, pform=pform)
        preply1 = create_preply(name='Reply#1')
        preply2 = create_preply(name='Reply#2')
        preply3 = create_preply(name='Reply#3')

        url = self._build_linkto_url(person)
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/link-popup.html')

        context = response.context
        self.assertEqual(
            _('Existing replies for «{entity}»').format(entity=person),
            context.get('title'),
        )
        self.assertEqual(_('Link to the replies'), context.get('submit_label'))

        # ---
        self.assertNoFormError(self.client.post(
            url, follow=True,
            data={'replies': self.formfield_value_multi_creator_entity(preply1, preply2)}
        ))

        person_id = person.id
        self.assertEqual(person_id, self.refresh(preply1).person_id)
        self.assertEqual(person_id, self.refresh(preply2).person_id)
        self.assertIsNone(self.refresh(preply3).person)

    @skipIfCustomContact
    def test_link_to_contact(self):
        user = self.login()
        self._aux_test_link_to(
            Contact.objects.create(user=user, first_name='Leina', last_name='Vance'),
        )

    @skipIfCustomOrganisation
    def test_link_to_orga(self):
        user = self.login()
        self._aux_test_link_to(Organisation.objects.create(user=user, name='Gaimos'))

    @skipIfCustomContact
    def test_link_to_creds(self):
        "Not super-user."
        user = self.login(is_superuser=False, allowed_apps=('creme_core', 'polls', 'persons'))
        SetCredentials.objects.create(
            role=self.role,
            value=EntityCredentials.VIEW | EntityCredentials.CHANGE | EntityCredentials.LINK,
            set_type=SetCredentials.ESET_ALL,
        )

        leina = Contact.objects.create(user=user, first_name='Leina', last_name='Vance')
        self.assertGET200(self._build_linkto_url(leina))

    @skipIfCustomContact
    def test_link_to_error01(self):
        "CHANGE credentials error."
        user = self.login(is_superuser=False, allowed_apps=('creme_core', 'polls', 'persons'))

        create_sc = partial(SetCredentials.objects.create, role=self.role)
        create_sc(
            value=EntityCredentials.CHANGE, set_type=SetCredentials.ESET_OWN,
        )
        create_sc(
            value=(
                EntityCredentials.VIEW
                | EntityCredentials.DELETE
                | EntityCredentials.LINK
                | EntityCredentials.UNLINK
                # | EntityCredentials.CHANGE
            ),
            set_type=SetCredentials.ESET_ALL,
        )

        pform = PollForm.objects.create(user=user, name='Form#1')
        preply = PollReply.objects.create(user=self.other_user, name='Reply#1', pform=pform)

        leina = Contact.objects.create(user=user, first_name='Leina', last_name='Vance')
        response = self.assertPOST200(
            self._build_linkto_url(leina),
            data={'replies': self.formfield_value_multi_creator_entity(preply)},
        )
        self.assertFormError(
            response, 'form', 'replies',
            _('Some entities are not editable: {}').format(preply),
        )

    @skipIfCustomActivity
    def test_link_to_error02(self):
        "Want to link to an Activity (not a Contact/Organisation)."
        self.login()
        self.assertGET404(self._build_linkto_url(self._create_activity()))

    @skipIfCustomContact
    def test_link_to_error03(self):
        "LINK credentials are needed"
        user = self.login(
            is_superuser=False, allowed_apps=('creme_core', 'polls', 'persons'),
        )
        SetCredentials.objects.create(
            role=self.role,
            value=EntityCredentials.VIEW | EntityCredentials.CHANGE,
            set_type=SetCredentials.ESET_ALL,
        )

        leina = Contact.objects.create(user=user, first_name='Leina', last_name='Vance')
        self.assertGET403(self._build_linkto_url(leina))

    def _aux_test_create_from_person(self, person):
        user = self.user

        url = self._build_preply_from_person_url(person)
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/add-popup.html')

        context = response.context
        self.assertEqual(
            _('New replies for «{entity}»').format(entity=person),
            context.get('title'),
        )
        self.assertEqual(PollReply.multi_save_label, context.get('submit_label'))

        with self.assertNoException():
            fields = context['form'].fields

        self.assertNotIn('number', fields)

        pform = PollForm.objects.create(user=user, name='Form#1')

        create_line = self._get_formline_creator(pform)
        create_line('Do you like swords?')
        create_line('What type of sword?')

        name = 'Reply'
        response = self.client.post(
            url,
            data={
                'user':  user.id,
                'name':  name,
                'pform': pform.id,
            }
        )
        self.assertNoFormError(response)

        replies = PollReply.objects.filter(pform=pform)
        self.assertEqual(1, len(replies))

        self.assertEqual(person.id, replies[0].person_id)

    @skipIfCustomContact
    def test_create_from_person01(self):
        "From a Contact."
        user = self.login()
        self._aux_test_create_from_person(
            Contact.objects.create(user=user, first_name='Leina', last_name='Vance')
        )

    @skipIfCustomOrganisation
    def test_create_from_person02(self):
        "From an Organisation."
        user = self.login()
        self._aux_test_create_from_person(
            Organisation.objects.create(user=user, name='Gaimos')
        )

    @skipIfCustomActivity
    def test_create_from_person03(self):
        "From an Activity --> error."
        self.login()
        self.assertGET404(self._build_preply_from_person_url(self._create_activity()))

    def test_create_from_person04(self):
        "Not super-user."
        user = self.login(
            is_superuser=False, allowed_apps=['polls', 'persons'],
            creatable_models=[PollReply],
        )
        SetCredentials.objects.create(
            role=self.role,
            value=(
                EntityCredentials.VIEW
                | EntityCredentials.CHANGE
                | EntityCredentials.DELETE
                | EntityCredentials.LINK
                | EntityCredentials.UNLINK
            ),
            set_type=SetCredentials.ESET_ALL,
        )
        orga = Organisation.objects.create(user=user, name='Gaimos')
        self.assertGET200(self._build_preply_from_person_url(orga))

    def test_create_from_person05(self):
        "Creation credentials are needed."
        user = self.login(
            is_superuser=False, allowed_apps=['polls', 'persons'],
            # creatable_models=[PollReply],
        )
        SetCredentials.objects.create(
            role=self.role,
            value=(
                EntityCredentials.VIEW
                | EntityCredentials.CHANGE
                | EntityCredentials.DELETE
                | EntityCredentials.LINK
                | EntityCredentials.UNLINK
            ),
            set_type=SetCredentials.ESET_ALL,
        )
        orga = Organisation.objects.create(user=user, name='Gaimos')
        self.assertGET403(self._build_preply_from_person_url(orga))

    def test_create_from_person06(self):
        "LINK credentials are needed."
        user = self.login(
            is_superuser=False, allowed_apps=['polls', 'persons'],
            creatable_models=[PollReply],
        )
        SetCredentials.objects.create(
            role=self.role,
            value=(
                EntityCredentials.VIEW
                | EntityCredentials.CHANGE
                | EntityCredentials.DELETE
                | EntityCredentials.UNLINK
                # | EntityCredentials.LINK
            ),
            set_type=SetCredentials.ESET_ALL,
        )
        orga = Organisation.objects.create(user=user, name='Gaimos')
        self.assertGET403(self._build_preply_from_person_url(orga))

    def test_editview01(self):
        user = self.login()
        ptype1, ptype2, ptype3 = PollType.objects.all()[:3]

        create_pform = partial(PollForm.objects.create, user=user)
        pform1 = create_pform(name='Form#1', type=ptype1)
        pform2 = create_pform(name='Form#2', type=ptype2)

        create_line = self._get_formline_creator(pform2)
        create_line('What type of swallow?')
        create_line('Do you like swallows?')

        name = 'reply#1'
        preply = PollReply.objects.create(user=user, pform=pform1, type=ptype1, name=name)

        url = preply.get_edit_absolute_url()
        self.assertGET200(url)

        name = name.title()
        response = self.client.post(
            url,
            follow=True,
            data={
                'user':  user.id,
                'name':  name,
                'pform': pform2.id,  # Will not change
                'type':  ptype3.id   # Should not be editable
            },
        )
        self.assertNoFormError(response)

        preply = self.refresh(preply)
        self.assertEqual(name,   preply.name)
        self.assertEqual(pform1, preply.pform)  # Not changed
        self.assertEqual(ptype1, preply.type)   # Not changed
        self.assertFalse(preply.lines.all())
        self.assertIsNone(preply.campaign)
        self.assertIsNone(preply.person)

    @skipIfCustomPollCampaign
    @skipIfCustomContact
    def test_editview02(self):
        "Edit campaign & person"
        user = self.login()
        pform  = PollForm.objects.create(user=user, name='Form#1')
        preply = PollReply.objects.create(name='Reply#1', user=user, pform=pform)

        camp = PollCampaign.objects.create(user=user, name='Camp#1')
        leina = Contact.objects.create(user=user, first_name='Leina', last_name='Vance')
        response = self.client.post(
            preply.get_edit_absolute_url(), follow=True,
            data={
                'user': user.id,
                'name': preply.name,
                'campaign': camp.id,
                'related_person': self.formfield_value_generic_entity(leina),
            },
        )
        self.assertNoFormError(response)

        preply = self.refresh(preply)
        self.assertEqual(camp,  preply.campaign)
        self.assertEqual(leina, preply.person.get_real_entity())

    @skipIfCustomPollCampaign
    @skipIfCustomContact
    def test_editview03(self):
        "Permissions for new related person"
        user = self.login(is_superuser=False, allowed_apps=('creme_core', 'polls', 'persons'))

        SetCredentials.objects.create(
            role=self.role,
            value=(
                EntityCredentials.VIEW
                | EntityCredentials.CHANGE
                | EntityCredentials.DELETE
                | EntityCredentials.LINK
                | EntityCredentials.UNLINK
            ),
            set_type=SetCredentials.ESET_OWN,
        )

        create_contact = partial(Contact.objects.create, last_name='Vance')
        leina     = create_contact(user=user,            first_name='Leina')
        claudette = create_contact(user=self.other_user, first_name='Claudette')
        erina     = create_contact(user=user,            first_name='Erina')

        pform = PollForm.objects.create(user=user, name='Form#1')
        preply = PollReply.objects.create(user=user, name='Reply#1', pform=pform, person=leina)

        def post(contact):
            return self.client.post(
                preply.get_edit_absolute_url(), follow=True,
                data={
                    'user':           user.id,
                    'name':           preply.name,
                    'related_person': self.formfield_value_generic_entity(contact),
                },
            )
        response = post(claudette)
        self.assertEqual(200, response.status_code)
        self.assertFormError(
            response, 'form', 'related_person',
            _('You are not allowed to link this entity: {}').format(
                _('Entity #{id} (not viewable)').format(id=claudette.id),
            )
        )

        self.assertNoFormError(post(erina))
        self.assertEqual(erina, self.refresh(preply).person.get_real_entity())

    @skipIfCustomPollCampaign
    @skipIfCustomContact
    def test_editview04(self):
        "No permissions checking on related person when not changed"
        user = self.login(is_superuser=False, allowed_apps=('creme_core', 'polls', 'persons'))

        SetCredentials.objects.create(
            role=self.role,
            value=(
                EntityCredentials.VIEW
                | EntityCredentials.CHANGE
                | EntityCredentials.DELETE
                | EntityCredentials.LINK
                | EntityCredentials.UNLINK
            ),
            set_type=SetCredentials.ESET_OWN,
        )

        leina = Contact.objects.create(
            user=self.other_user, first_name='Leina', last_name='Vance',
        )

        pform = PollForm.objects.create(user=user, name='Form#1')
        preply = PollReply.objects.create(user=user, name='Reply#1', pform=pform, person=leina)

        name = preply.name.upper()
        response = self.client.post(
            preply.get_edit_absolute_url(), follow=True,
            data={
                'user':           user.id,
                'name':           name,
                'related_person': self.formfield_value_generic_entity(leina),
            },
        )
        self.assertNoFormError(response)

        preply = self.refresh(preply)
        self.assertEqual(name, preply.name)
        self.assertEqual(leina, preply.person.get_real_entity())

    def test_inneredit01(self):
        user = self.login()
        pform  = PollForm.objects.create(user=user, name='Form#1')
        preply = PollReply.objects.create(name='Reply#1', user=user, pform=pform)

        url = self.build_inneredit_url(preply, 'name')
        self.assertGET200(url)

        name = preply.name + ' (edited)'
        response = self.client.post(
            url,
            data={
                'entities_lbl': [str(preply)],
                'field_value':  name,
            },
        )
        self.assertNoFormError(response)
        self.assertEqual(name, self.refresh(preply).name)

    def test_inneredit02(self):
        "Inner edition: 'pform' field is not editable."
        user = self.login()

        create_pform = partial(PollForm.objects.create, user=user)
        pform1 = create_pform(name='Form#1')
        pform2 = create_pform(name='Form#2')

        preply = PollReply.objects.create(name='Reply#1', user=user, pform=pform1)

        self.assertPOST(
            400,
            self.build_inneredit_url(preply, 'pform'),
            data={
                'entities_lbl': [str(preply)],
                'field_value':  pform2.id,
            },
        )
        self.assertEqual(pform1, self.refresh(preply).pform)

    @skipIfCustomContact
    def test_inneredit03(self):
        "Inner edition: 'person' field."
        user = self.login()

        pform  = PollForm.objects.create(user=user, name='Form#1')
        preply = PollReply.objects.create(name='Reply#1', user=user, pform=pform)

        url = self.build_inneredit_url(preply, 'person')
        self.assertGET200(url)

        leina = Contact.objects.create(user=user, first_name='Leina', last_name='Vance')
        self.assertNoFormError(self.client.post(
            url,
            data={
                'entities_lbl': [str(preply)],
                'field_value':  self.formfield_value_generic_entity(leina),
            },
        ))
        self.assertEqual(leina, self.refresh(preply).person.get_real_entity())

    @skipIfCustomContact
    def test_inneredit04(self):
        "Inner edition: 'person' field + not super user"
        user = self.login(is_superuser=False, allowed_apps=('creme_core', 'polls', 'persons'))

        create_sc = partial(SetCredentials.objects.create, role=self.role)
        create_sc(value=EntityCredentials.LINK, set_type=SetCredentials.ESET_OWN)
        create_sc(
            value=(
                EntityCredentials.VIEW
                | EntityCredentials.DELETE
                | EntityCredentials.CHANGE
                | EntityCredentials.UNLINK
                # | EntityCredentials.LINK
            ),
            set_type=SetCredentials.ESET_ALL,
        )

        pform  = PollForm.objects.create(user=user, name='Form#1')
        preply = PollReply.objects.create(name='Reply#1', user=user, pform=pform)

        url = self.build_inneredit_url(preply, 'person')

        create_contact = Contact.objects.create
        leina = create_contact(user=self.other_user, first_name='Leina', last_name='Vance')
        response = self.client.post(
            url,
            data={
                'entities_lbl': [str(preply)],
                'field_value':  self.formfield_value_generic_entity(leina),
            },
        )
        self.assertFormError(
            response, 'form', 'field_value',
            _('You are not allowed to link this entity: {}').format(leina),
        )

        # ----
        claudette = create_contact(user=user, first_name='Claudette', last_name='Vance')
        response = self.client.post(
            url,
            data={
                'entities_lbl': [str(preply)],
                'field_value':  self.formfield_value_generic_entity(claudette),
            },
        )
        self.assertNoFormError(response)
        self.assertEqual(claudette, self.refresh(preply).person.get_real_entity())

    @skipIfCustomContact
    def test_inneredit05(self):
        "Inner edition: 'person' field (set None)."
        user = self.login()

        leina = Contact.objects.create(user=user, first_name='Leina', last_name='Vance')
        pform = PollForm.objects.create(user=user, name='Form#1')
        preply = PollReply.objects.create(name='Reply#1', user=user, pform=pform, person=leina)

        response = self.client.post(self.build_inneredit_url(preply, 'person'))
        self.assertNoFormError(response)
        self.assertIsNone(self.refresh(preply).person)

    def test_listview(self):
        user = self.login()
        pform = PollForm.objects.create(user=user, name='Form#1')

        create_reply = partial(PollReply.objects.create, user=user, pform=pform)
        preply1 = create_reply(name='Reply#1')
        preply2 = create_reply(name='Reply#2')

        response = self.assertGET200(PollReply.get_lv_absolute_url())

        with self.assertNoException():
            preply_page = response.context['page_obj']

        self.assertEqual(2, preply_page.paginator.count)
        self.assertSetEqual({preply1, preply2}, {*preply_page.object_list})

    def test_delete_type(self):
        "Set to NULL."
        self.login()
        ptype  = PollType.objects.create(name='Political poll')
        preply = self._build_preply(ptype=ptype)

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

    def test_section_tree(self):
        user = self.login()
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

        preply = self._build_preply_from_pform(pform, 'Reply#1')

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

    def test_fillview_string01(self):
        "Fill one STRING question"
        self.login()
        pform = PollForm.objects.create(user=self.user, name='Form#1')
        fline = self._get_formline_creator(pform)('What is the difference between a swallow?')

        preply = self._build_preply_from_pform(pform, 'Reply#1')
        rline  = PollReplyLine.objects.get(pform_line=fline)

        url = self._build_fill_url(preply)
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/edit.html')

        context = response.context
        self.assertEqual(_('Answers of the form : {}').format(preply), context.get('title'))
        self.assertEqual(preply.get_absolute_url(),                    context.get('cancel_url'))
        self.assertIsNone(context.get('help_message'))

        with self.assertNoException():
            question_f = context['form'].fields['question']

        self.assertEqual(f'1 - {fline.question}', question_f.initial)

        answer = 'The 2 legs are equal, almost the right one.'
        self.assertNoFormError(self.client.post(url, follow=True, data={'answer': answer}))

        rline = self.refresh(rline)
        self.assertEqual(answer, rline.answer)
        self.assertTrue(rline.applicable)

    def test_fillview_text01(self):
        "Fill one TEXT question (not empty)."
        self.login()
        preply, rline = self._build_reply_with_text_line()

        answer = 'The 2 legs are equal, almost the right one.'
        self.assertNoFormError(self._fill(preply, answer))
        self.assertEqual(answer, self.refresh(rline).answer)

    def test_fillview_text02(self):
        "Fill one TEXT question (empty)."
        self.login()
        preply, rline = self._build_reply_with_text_line()
        answer = ''
        self.assertNoFormError(self._fill(preply, answer))
        self.assertEqual(answer, self.refresh(rline).answer)

    def test_fillview_int01(self):
        "Fill one INT question."
        self.login()
        preply, rline = self._build_reply_with_int_line()
        self.assertFormError(
            self._fill(preply, 'notanint', check_errors=False),
            'form', 'answer', [_('Enter a whole number.')],
        )

        answer = 42
        self.assertNoFormError(self._fill(preply, answer))
        self.assertEqual(answer, self.refresh(rline).answer)

    def test_fillview_int02(self):
        "Fill one INT question with bounds."
        self.login()
        lower_bound = 10
        upper_bound = 20
        preply, rline = self._build_reply_with_int_line(lower_bound, upper_bound)
        self.assertFormError(
            self._fill(preply, 5, check_errors=False), 'form', 'answer',
            _('Ensure this value is greater than or equal to %(limit_value)s.') % {
                'limit_value': lower_bound,
            },
        )

        self.assertFormError(
            self._fill(preply, 25, check_errors=False), 'form', 'answer',
            _('Ensure this value is less than or equal to %(limit_value)s.') % {
                'limit_value': upper_bound,
            },
        )

        answer = 15
        self.assertNoFormError(self._fill(preply, answer))
        rline_answer = self.refresh(rline).answer
        self.assertEqual(answer, rline_answer, type(rline_answer))

    def test_fillview_bool01(self):
        "Fill one BOOL question (True)."
        self.login()
        preply, rline = self._build_reply_with_bool_line()
        self.assertNoFormError(self._fill(preply, 1))
        self.assertEqual(_('Yes'), self.refresh(rline).answer)

    def test_fillview_bool02(self):
        "Fill one BOOL question (False)."
        self.login()
        preply, rline = self._build_reply_with_bool_line()
        self.assertNoFormError(self._fill(preply, 0))
        rline = self.refresh(rline)
        self.assertEqual('0',     rline.raw_answer)
        self.assertEqual(_('No'), rline.answer)

    def test_fillview_bool03(self):
        "Fill one BOOL question : no answer (caused an issue)."
        self.login()
        preply, rline = self._build_reply_with_bool_line()
        self.assertFormError(
            self.client.post(self._build_fill_url(preply), follow=True),
            'form', 'answer', _('The answer is required.'),
        )

    def test_fillview_date01(self):
        "One DATE question"
        self.login()
        pform = PollForm.objects.create(user=self.user, name='Form#1')
        fline = self._get_formline_creator(pform)(
            'When is your birthday?', qtype=PollLineType.DATE,
        )
        preply = self._build_preply_from_pform(pform, 'Reply#1')
        rline  = self.get_object_or_fail(PollReplyLine, pform_line=fline)

        self.assertFormError(
            self._fill(preply, 'notanint', check_errors=False),
            'form', 'answer', _('Enter a valid date.'),
        )

        self.assertNoFormError(self._fill(preply, '8-6-2012'))
        self.assertEqual(date(year=2012, month=6, day=8), self.refresh(rline).answer)

    def test_fillview_hour01(self):
        "One HOUR question"
        self.login()
        pform = PollForm.objects.create(user=self.user, name='Form#1')
        fline = self._get_formline_creator(pform)(
            'What is the best hour to see a killer rabbit?',
            qtype=PollLineType.HOUR,
        )
        preply = self._build_preply_from_pform(pform, 'Reply#1')
        rline  = self.get_object_or_fail(PollReplyLine, pform_line=fline)

        self.assertFormError(
            self._fill(preply, -1, check_errors=False), 'form', 'answer',
            _('Ensure this value is greater than or equal to %(limit_value)s.') % {
                'limit_value': 0,
            },
        )
        self.assertFormError(
            self._fill(preply, 24, check_errors=False), 'form', 'answer',
            _('Ensure this value is less than or equal to %(limit_value)s.') % {
                'limit_value': 23,
            },
        )

        self._fill(preply, '17')
        self.assertEqual(17, self.refresh(rline).answer)

    def test_fillview_enum01(self):
        "Fill one ENUM question."
        self.login()
        pform = PollForm.objects.create(user=self.user, name='Form#1')
        choices = [[1, 'White'], [2, 'Black'], [3, 'Green']]
        fline = self._get_formline_creator(pform)(
            'What is the main color of a swallow?',
            qtype=PollLineType.ENUM, choices=choices,
        )

        preply = self._build_preply_from_pform(pform, 'Reply#1')
        rline  = PollReplyLine.objects.get(pform_line=fline)

        response = self.assertGET200(self._build_fill_url(preply))

        with self.assertNoException():
            answer_field = response.context['form'].fields['answer']

        self.assertEqual(choices, answer_field.choices)
        self.assertIsInstance(answer_field.widget, Select)

        answer = 'Invalid choice'
        self.assertFormError(
            self._fill(preply, answer, check_errors=False), 'form', 'answer',
            _('Select a valid choice. %(value)s is not one of the available choices.') % {
                'value': answer
            },
        )

        self.assertFormError(
            self.client.post(self._build_fill_url(preply), follow=True),
            'form', 'answer', _('The answer is required.'),
        )

        self.assertNoFormError(self._fill(preply, 2))

        rline_answer = self.refresh(rline).answer
        self.assertEqual('Black', rline_answer, type(rline_answer))

    def test_fillview_multienum01(self):
        "Fill one MULTI_ENUM question."
        user = self.login()
        pform = PollForm.objects.create(user=user, name='Form#1')

        choices = [[1, 'White'], [2, 'Black'], [3, 'Green'], [4, 'Purple']]
        fline = self._get_formline_creator(pform)(
            'What are the main colors of a swallow?',
            qtype=PollLineType.MULTI_ENUM,
            choices=choices,
        )

        preply = self._build_preply_from_pform(pform, 'Reply#1')
        rline  = PollReplyLine.objects.get(pform_line=fline)

        response = self.assertGET200(self._build_fill_url(preply))

        with self.assertNoException():
            answer_field = response.context['form'].fields['answer']

        self.assertEqual(choices, answer_field.choices)
        self.assertIsInstance(answer_field.widget, UnorderedMultipleChoiceWidget)

        self.assertFormError(
            self._fill(preply, [5, 7], check_errors=False), 'form', 'answer',
            _('Select a valid choice. %(value)s is not one of the available choices.') % {
                'value': 5
            },
        )

        self.assertNoFormError(self._fill(preply, [1, 2]))

        rline_answer = self.refresh(rline).answer
        self.assertEqual(['White', 'Black'], rline_answer, type(rline_answer))

    def test_fillview_enumorstring01(self):
        "Fill one ENUM_OR_STRING question."
        self.login()
        preply, rline = self._build_reply_with_enumorstring_line()
        answer = 42
        self.assertFormError(
            self._fill(preply, {'answer_0': answer, 'answer_1': ''}, check_errors=False),
            'form', 'answer',
            _('Select a valid choice. %(value)s is not one of the available choices.') % {
                'value': answer,
            },
        )

        self.assertNoFormError(self._fill(preply, {'answer_0': 2, 'answer_1': ''}))

        rline_answer = self.refresh(rline).answer
        self.assertEqual('Black', rline_answer, type(rline_answer))

    def test_fillview_enumorstring02(self):
        "Fill one ENUM_OR_STRING question --> 'free' choice."
        self.login()
        preply, rline = self._build_reply_with_enumorstring_line()

        answer = 'Red'
        self.assertNoFormError(self._fill(preply, {'answer_0': 0, 'answer_1': answer}))

        rline_answer = self.refresh(rline).answer
        self.assertEqual(answer, rline_answer, type(rline_answer))

    def test_fillview_comment01(self):
        "Fill one COMMENT question."
        self.login()
        pform = PollForm.objects.create(user=self.user, name='Form#1')
        fline = PollFormLine.objects.create(
            pform=pform, type=PollLineType.COMMENT,
            question='Beware, the next questions talk about weird things !'
        )
        preply = self._build_preply_from_pform(pform, 'Reply#1')
        rline  = self.get_object_or_fail(PollReplyLine, pform_line=fline)

        response = self.assertGET200(self._build_fill_url(preply))

        with self.assertNoException():
            fields = response.context['form'].fields

        self.assertNotIn('not_applicable', fields)

        self.assertNoFormError(self._fill(preply, ''))
        self.assertEqual('', self.refresh(rline).answer)
        self.assertTrue(self.refresh(preply).is_complete)

    def test_fillview_not_applicable01(self):
        self.login()
        preply, rline = self._build_reply_with_int_line()
        self._fill(preply, '', not_applicable=True)

        rline = self.refresh(rline)
        self.assertIsNone(rline.answer)
        self.assertFalse(rline.applicable)

    def test_fillview_not_applicable02(self):
        "If the answer is applicable, 'answer' field is required."
        self.login()
        preply, rline = self._build_reply_with_int_line()
        self.assertFormError(
            self._fill(preply, '', not_applicable=False, check_errors=False),
            'form', 'answer', _('The answer is required.'),
        )

    def test_fillview_wizard01(self):
        "Wizard with 2 questions."
        self.login()
        preply, rline1, rline2 = self._build_reply_with_2_lines()

        answer = 8
        self._fill(preply, answer)
        self.assertEqual(answer, self.refresh(rline1).answer)
        self.assertFalse(self.refresh(preply).is_complete)

        response = self.client.get(self._build_fill_url(preply))

        with self.assertNoException():
            question_f = response.context['form'].fields['question']

        self.assertEqual(f'2 - {rline2.question}', question_f.initial)
        self.assertContains(response, f'1 - {rline1.question}')

        answer = 'Betty'
        response = self._fill(preply, answer)
        self.assertEqual(answer, self.refresh(rline2).answer)
        self.assertRedirects(response, preply.get_absolute_url())
        self.assertTrue(self.refresh(preply).is_complete)

        self.assertGET404(self._build_fill_url(preply))  # All questions are answered

    def test_fillview_wizard02(self):
        "Wizard: no line (SHOULD NOT HAPPEN...)."
        self.login()
        preply = self._build_preply()
        self.assertGET404(self._build_fill_url(preply))

    def test_fillview_wizard03(self):
        "Wizard: with a condition (that is OK)."
        self.login()
        self._build_rlines_with_condition()
        self.assertFalse(self.rcondition.is_met(self.rline1))
        self.assertCurrentQuestion(self._fill(self.preply, 2), self.fline2, 2)

    def test_fillview_wizard04(self):
        "Wizard: condition (that is false)."
        self.login()
        self._build_rlines_with_condition()
        self.assertCurrentQuestion(self._fill(self.preply, 1), self.fline3)

    def test_fillview_wizard05(self):
        "Wizard: condition (false) + no more question."
        self.login()
        self._build_rlines_with_condition(only_2_questions=True)

        self._fill(self.preply, 1)
        self.assertTrue(self.refresh(self.preply).is_complete)

    def test_fillview_wizard06(self):
        "Wizard: complex conditions (OK and OK)."
        self.login()
        self._build_rlines_with_conditions()
        self.assertCurrentQuestion(self._fill(self.preply, 2), self.fline2)
        self.assertCurrentQuestion(self._fill(self.preply, 2), self.fline3)

    def test_fillview_wizard07(self):
        "Wizard: complex conditions (OK and KO)."
        self.login()
        self._build_rlines_with_conditions()
        self.assertCurrentQuestion(self._fill(self.preply, 2), self.fline2)

        self._fill(self.preply, 1)
        self.assertTrue(self.refresh(self.preply).is_complete)

    def test_fillview_wizard08(self):
        "Wizard: complex conditions (KO or OK)."
        self.login()
        self._build_rlines_with_conditions(conds_use_or=True)
        self.assertCurrentQuestion(self._fill(self.preply, 1), self.fline2)
        self.assertCurrentQuestion(self._fill(self.preply, 2), self.fline3)

    def test_fillview_wizard09(self):
        "Wizard: 'N/A' == condition is false."
        self.login()
        self._build_rlines_with_condition()
        self.assertCurrentQuestion(self._fill(self.preply, '', not_applicable=True), self.fline3)

    def test_fillview_wizard_multienum01(self):
        "Wizard: answer in choices of condition (MULTI_ENUM question)."
        self.login()
        self._build_rlines_with_conditions_on_multienum()
        self.assertFalse(self.rcondition.is_met(self.rline1))
        self.assertCurrentQuestion(self._fill(self.preply, 1), self.fline2)

    def test_fillview_wizard_multienum02(self):
        "Wizard: answer not in choices of condition (MULTI_ENUM question)."
        self.login()
        self._build_rlines_with_conditions_on_multienum()
        self._fill(self.preply, 2)
        self.assertTrue(self.refresh(self.preply).is_complete)

    def test_fillview_wizard_multienum03(self):
        "Wizard: one answer in choices of condition (MULTI_ENUM question)."
        self.login()
        self._build_rlines_with_conditions_on_multienum()
        self.assertCurrentQuestion(self._fill(self.preply, [1, 2]), self.fline2)

    def test_fillview_wizard_multienum04(self):
        "Wizard: no answer in choices of condition (MULTI_ENUM question)."
        self.login()
        self._build_rlines_with_conditions_on_multienum()
        self._fill(self.preply, [3, 4])
        self.assertTrue(self.refresh(self.preply).is_complete)

    def test_fillview_wizard_enumorstring01(self):
        "Wizard: condition on the regular choice 'True' (MULTI_ENUM question)."
        self.login()
        self._build_rlines_with_conditions_on_enumorstring(1)
        self.assertFalse(self.rcondition.is_met(self.rline1))
        self.assertCurrentQuestion(
            self._fill(self.preply, {'answer_0': 1, 'answer_1': ''}),
            self.fline2,
        )

    def test_fillview_wizard_enumorstring02(self):
        "Wizard: condition on the regular choice 'False' (MULTI_ENUM question)."
        self.login()
        self._build_rlines_with_conditions_on_enumorstring(1)
        self._fill(self.preply, {'answer_0': 2, 'answer_1': ''})
        self.assertTrue(self.refresh(self.preply).is_complete)

    def test_fillview_wizard_enumorstring03(self):
        "Wizard: condition (that is True) on 'Other' choice (MULTI_ENUM question)."
        self.login()
        self._build_rlines_with_conditions_on_enumorstring(0)
        self.assertCurrentQuestion(
            self._fill(self.preply, {'answer_0': 0, 'answer_1': 'Pistachio'}),
            self.fline2,
        )

    def test_fillview_wizard_enumorstring04(self):
        "Wizard: condition (that is False) on 'Other' choice (MULTI_ENUM question)."
        self.login()
        self._build_rlines_with_conditions_on_enumorstring(0)
        self._fill(self.preply, {'answer_0': 2, 'answer_1': ''})
        self.assertTrue(self.refresh(self.preply).is_complete)

    def test_fillview_wizard_bool01(self):
        self.login()
        self._build_rlines_with_conditions_on_bool()
        self.assertFalse(self.rcondition.is_met(self.rline1))
        self.assertCurrentQuestion(self._fill(self.preply, 1), self.fline2)

    def test_fillview_wizard_bool02(self):
        "Wizard: BOOL question that causes false condition."
        self.login()
        self._build_rlines_with_conditions_on_bool()
        self._fill(self.preply, 0)
        self.assertTrue(self.refresh(self.preply).is_complete)

    def test_fillview_wizard_not_applicable01(self):
        self.login()
        preply, rline1, rline2 = self._build_reply_with_2_lines()

        self._fill(preply, '', not_applicable=True)
        self.assertFalse(self.refresh(rline1).applicable)

        self.assertContains(
            self.client.get(self._build_fill_url(preply)),
            f'1 - {rline1.question}',
        )

        answer = 'Betty'
        self._fill(preply, answer)
        self.assertEqual(answer, self.refresh(rline2).answer)
        self.assertTrue(self.refresh(preply).is_complete)

    def test_fillview_wizard_not_applicable02(self):
        "Wizard: answer is not applicable (but we still post a valid answer)."
        self.login()
        preply, rline = self._build_reply_with_int_line()
        self._fill(preply, 12, not_applicable=True)
        self.assertTrue(self.refresh(preply).is_complete)

        rline = self.refresh(rline)
        self.assertFalse(rline.applicable)
        self.assertIsNone(rline.raw_answer)

    def test_clean_answers(self):
        self.login()
        preply, rline1, rline2 = self._build_reply_with_2_lines()
        self._fill(preply, '56')
        self._fill(preply, '', not_applicable=True)
        self.assertTrue(self.refresh(preply).is_complete)

        self.assertPOST200(reverse('polls__clean_reply'), follow=True, data={'id': preply.id})
        self.assertFalse(self.refresh(preply).is_complete)

        rline1 = self.refresh(rline1)
        self.assertIsNone(rline1.answer)
        self.assertTrue(rline1.applicable)

        rline2 = self.refresh(rline2)
        self.assertIsNone(rline2.answer)
        self.assertTrue(rline2.applicable)

    def test_edit_answer01(self):
        "Edit answer: one INT answer already answered."
        user = self.login()
        pform = PollForm.objects.create(user=user, name='Form#1')
        question = 'How many swallows are there?'
        fline = self._get_formline_creator(pform)(question, qtype=PollLineType.INT)

        preply = self._build_preply_from_pform(pform, 'Reply#1')
        rline = self.get_object_or_fail(PollReplyLine, pform_line=fline)

        old_answer = 56
        self._fill(preply, old_answer)
        self.assertTrue(self.refresh(preply).is_complete)

        response = self.assertGET200(self._build_edit_answer_url(preply, rline))
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/edit-popup.html')

        context = response.context
        self.assertEqual(_('Answer edition'),        context.get('title'))
        self.assertEqual(_('Save the modification'), context.get('submit_label'))

        with self.assertNoException():
            fields = context['form'].fields

        self.assertIn('question', fields)
        self.assertEqual(f'1 - {question}', fields['question'].initial)
        self.assertIn('answer', fields)
        self.assertEqual(old_answer, fields['answer'].initial)

        self.assertIn('not_applicable', fields)
        self.assertFalse(fields['not_applicable'].initial)

        self._edit_answer(preply, rline, answer=42, is_complete=True)

    def test_edit_answer02(self):
        "Edit answer: one INT answer not answered (so reply becomes fully filled)."
        self.login()
        pform = PollForm.objects.create(user=self.user, name='Form#1')
        fline = self._get_formline_creator(pform)(
            'How many swallows are there?',
            qtype=PollLineType.INT,
        )
        preply = self._build_preply_from_pform(pform, 'Reply#1')
        self.assertFalse(preply.is_complete)

        rline = self.get_object_or_fail(PollReplyLine, pform_line=fline)
        self._edit_answer(preply, rline, answer=42, is_complete=True)

    def test_edit_answer03(self):
        "Edit answer: 2 STRING answers not answered -> we edit the second one first."
        self.login()
        pform = PollForm.objects.create(user=self.user, name='Form#1')

        create_line = self._get_formline_creator(pform)
        fline1 = create_line('What is your name?')
        fline2 = create_line('What is your nick name?')

        preply = self._build_preply_from_pform(pform, 'Reply#1')
        self.assertFalse(preply.is_complete)

        rline1 = self.get_object_or_fail(PollReplyLine, pform_line=fline1)
        rline2 = self.get_object_or_fail(PollReplyLine, pform_line=fline2)

        self._edit_answer(preply, rline2, answer='The brave', is_complete=False)
        self._edit_answer(preply, rline1, answer='Arthur',    is_complete=True)

    def test_edit_answer04(self):
        """Edit answer : 3 BOOL answers ; the 2 first are already filled, we
        edit the first (line order > edited order).
        """
        self.login()
        pform = PollForm.objects.create(user=self.user, name='Form#1')

        create_line = partial(PollFormLine.objects.create, pform=pform, type=PollLineType.BOOL)
        flines = [
            create_line(order=i, question=question)
            for i, question in enumerate(('OK?', 'Alright?', 'Cool?'), start=1)
        ]

        preply = self._build_preply_from_pform(pform, 'Reply#1')

        self._fill(preply, 0, 1)
        self.assertFalse(self.refresh(preply).is_complete)

        rline = self.get_object_or_fail(PollReplyLine, pform_line=flines[0])
        self._edit_answer(preply, rline, answer=1, is_complete=False)

    def test_edit_answer05(self):
        """Edit answer : 2 filled lines with a condition -> dependant line is
        cleared ('is_complete' changes too).
        """
        self.login()
        self._build_rlines_with_condition(only_2_questions=True)

        preply = self.preply
        self._fill(preply, 2, 'Asian ones')
        self.assertTrue(self.refresh(preply).is_complete)

        self._edit_answer(preply, self.rline1, answer=1, is_complete=True)
        self.assertIsNone(self.refresh(self.rline2).raw_answer)

    def test_edit_answer06(self):
        "Idem, but this time condition become True."
        self.login()
        self._build_rlines_with_condition(only_2_questions=True)

        preply = self.preply
        self._fill(preply, 1)
        self.assertTrue(self.refresh(preply).is_complete)

        self._edit_answer(preply, self.rline1, answer=2, is_complete=False)
        self.assertIsNone(self.refresh(self.rline2).raw_answer)

    def test_edit_answer07(self):
        "Edit answer: chain of conditions dependencies."
        user = self.login()
        pform = PollForm.objects.create(user=user, name='Form#1')

        create_line = self._get_formline_creator(pform)
        fline1 = create_line('Do you like swallows?', qtype=PollLineType.BOOL)
        fline2 = create_line(
            'How do you like swallows?', qtype=PollLineType.ENUM,
            conds_use_or=True, choices=[[1, 'A little'], [2, 'A lot']],
        )
        fline3 = create_line('Why do you love them so much?', conds_use_or=True)

        create_cond = partial(
            PollFormLineCondition.objects.create,
            operator=PollFormLineCondition.EQUALS
        )
        create_cond(line=fline2, source=fline1, raw_answer='1')
        create_cond(line=fline3, source=fline2, raw_answer='2')

        preply = self._build_preply_from_pform(pform, 'Reply#1')
        rline1 = self.get_object_or_fail(PollReplyLine, pform_line=fline1)
        rline2 = self.get_object_or_fail(PollReplyLine, pform_line=fline2)
        rline3 = self.get_object_or_fail(PollReplyLine, pform_line=fline3)

        self._fill(preply, 1, 2, 'They so beautiful !')
        self.assertTrue(self.refresh(preply).is_complete)

        self._edit_answer(preply, rline1, answer=0, is_complete=True)
        self.assertIsNone(self.refresh(rline2).raw_answer)
        self.assertIsNone(self.refresh(rline3).raw_answer)

    def test_edit_answer08(self):
        "Edit answer: can not edit an answer when related conditions are false."
        self.login()
        self._build_rlines_with_condition()

        preply = self.preply
        self._fill(preply, 1)
        self.assertFalse(self.refresh(preply).is_complete)
        self.assertGET404(self._build_edit_answer_url(preply, self.rline2))

    def test_edit_answer_not_applicable01(self):
        "Edit answer: edit a not applicable answer."
        self.login()
        preply, rline = self._build_reply_with_int_line()
        self._fill(preply, '', not_applicable=True)

        response = self.client.get(self._build_edit_answer_url(preply, rline))

        with self.assertNoException():
            fields = response.context['form'].fields
            answer_f = fields['answer']
            na_f = fields['not_applicable']

        self.assertFalse(answer_f.initial)
        self.assertTrue(na_f.initial)

    def test_edit_answer_not_applicable02(self):
        "Edit answer: edit an answer to set it not applicable."
        self.login()
        preply, rline = self._build_reply_with_int_line()
        self._fill(preply, 12)

        self.assertPOST200(
            self._build_edit_answer_url(preply, rline),
            data={'answer': 12, 'not_applicable': 'on'}
        )
        rline = self.refresh(rline)
        self.assertFalse(rline.applicable)
        self.assertIsNone(rline.raw_answer)

    def test_edit_answer_not_superuser01(self):
        self.login(
            is_superuser=False, allowed_apps=['polls'], creatable_models=[PollReply],
        )
        SetCredentials.objects.create(
            role=self.role,
            value=(
                EntityCredentials.VIEW
                | EntityCredentials.CHANGE
                | EntityCredentials.DELETE
                | EntityCredentials.LINK
                | EntityCredentials.UNLINK
            ),
            set_type=SetCredentials.ESET_ALL,
        )

        pform = PollForm.objects.create(user=self.user, name='Form#1')
        question = 'How many swallows are there?'
        fline = self._get_formline_creator(pform)(question, qtype=PollLineType.INT)

        preply = self._build_preply_from_pform(pform, 'Reply#1')
        rline = self.get_object_or_fail(PollReplyLine, pform_line=fline)

        old_answer = 56
        self._fill(preply, old_answer)
        self.assertTrue(self.refresh(preply).is_complete)

        self.assertGET200(self._build_edit_answer_url(preply, rline))

    def test_edit_answer_not_superuser02(self):
        "Edition permission on PollReply is needed."
        self.login(
            is_superuser=False, allowed_apps=['polls'], creatable_models=[PollReply],
        )
        SetCredentials.objects.create(
            role=self.role,
            value=(
                EntityCredentials.VIEW
                | EntityCredentials.DELETE
                | EntityCredentials.LINK
                | EntityCredentials.UNLINK
                # | EntityCredentials.CHANGE
            ),
            set_type=SetCredentials.ESET_ALL,
        )

        pform = PollForm.objects.create(user=self.user, name='Form#1')
        question = 'How many swallows are there?'
        fline = self._get_formline_creator(pform)(question, qtype=PollLineType.INT)

        preply = self._build_preply_from_pform(pform, 'Reply#1')
        rline = self.get_object_or_fail(PollReplyLine, pform_line=fline)

        PollReply.objects.filter(id=preply.id).update(is_complete=True)
        self.assertGET403(self._build_edit_answer_url(preply, rline))

    def test_edit_wizard01(self):
        "Edition wizard: without conditions."
        self.login()
        pform  = PollForm.objects.create(user=self.user, name='Form#1')

        create_line = self._get_formline_creator(pform)
        fline1 = create_line('What is your name?')
        fline2 = create_line('What is your nick name?')

        preply = self._build_preply_from_pform(pform, 'Reply#1')
        self.assertFalse(preply.is_complete)

        rline1 = self.get_object_or_fail(PollReplyLine, pform_line=fline1)
        rline2 = self.get_object_or_fail(PollReplyLine, pform_line=fline2)

        self._fill(preply, 1)
        self.assertFalse(self.refresh(preply).is_complete)

        response = self.assertGET200(self._build_edit_wizard_answer_url(preply, rline1))
        self.assertContains(response, rline1.question)

        self._edit_wizard_answer(preply, rline1, answer='0', is_complete=False)

        self.assertIsNone(self.refresh(rline2).raw_answer)
        self.assertFalse(self.refresh(preply).is_complete)

    def test_edit_wizard02(self):
        "Edition wizard: with a condition already met."
        self.login()
        self._build_rlines_with_condition()

        preply = self.preply
        self._fill(preply, 2, 1)
        self.assertFalse(self.refresh(preply).is_complete)

        self._edit_wizard_answer(preply, self.rline1, answer=1, is_complete=False)
        self.assertIsNone(self.refresh(self.rline2).raw_answer)

    def test_edit_wizard03(self):
        "Edition wizard: with a condition that becomes false."
        self.login()
        self._build_rlines_with_condition()

        preply = self.preply
        self._fill(preply, 1, '3')
        self.assertTrue(self.refresh(preply).is_complete)

        self._edit_wizard_answer(preply, self.rline1, answer=2, is_complete=False)
        self.assertIsNone(self.refresh(self.rline2).raw_answer)

    def test_edit_initialised_enum_answer(self):
        "One ENUM answer already answered"
        self.login()
        pform = PollForm.objects.create(user=self.user, name='Form#1')
        fline = self._get_formline_creator(pform)(
            'What type of swallow?',
            qtype=PollLineType.ENUM, choices=[[1, 'European'], [2, 'African']],
        )
        preply = self._build_preply_from_pform(pform, 'Reply#1')
        rline = self.get_object_or_fail(PollReplyLine, pform_line=fline)

        old_answer = 1
        self._fill(preply, old_answer)
        self.assertTrue(self.refresh(preply).is_complete)

        response = self.assertGET200(self._build_edit_answer_url(preply, rline))

        with self.assertNoException():
            answer_f = response.context['form'].fields['answer']

        self.assertEqual(old_answer, answer_f.initial)

    def test_edit_initialised_date_answer(self):
        "One DATE answer already answered."
        user = self.login()
        pform = PollForm.objects.create(user=user, name='Form#1')
        fline = self._get_formline_creator(pform)(
            'When is your birthday?', qtype=PollLineType.DATE,
        )
        preply = self._build_preply_from_pform(pform, 'Reply#1')
        rline = self.get_object_or_fail(PollReplyLine, pform_line=fline)

        self._fill(preply, '19-09-2012')
        self.assertTrue(self.refresh(preply).is_complete)

        response = self.assertGET200(self._build_edit_answer_url(preply, rline))

        with self.assertNoException():
            answer_f = response.context['form'].fields['answer']

        self.assertEqual(date(year=2012, month=9, day=19), answer_f.initial)

    # TODO: test other type initial ???

    def test_edit_answer_n_fill(self):
        "Does fill view manage answers already filled"
        user = self.login()
        pform = PollForm.objects.create(user=user, name='Form#1')

        create_line = partial(PollFormLine.objects.create, pform=pform, type=PollLineType.BOOL)
        flines = [
            create_line(order=i, question=question)
            for i, question in enumerate(('OK?', 'Alright?', 'Cool?'), start=1)
        ]

        preply = self._build_preply_from_pform(pform, 'Reply#1')

        rline = self.get_object_or_fail(PollReplyLine, pform_line=flines[1])
        self._edit_answer(preply, rline, answer=1, is_complete=False)

        self._fill(preply, 0, 1)
        self.assertTrue(self.refresh(preply).is_complete)

    def _build_rline_for_stat(self, type, answer, choices=None):
        pform = PollForm.objects.create(user=self.user, name='Form#1')
        fline = self._get_formline_creator(pform)(
            'What do you think about swallows?', qtype=type, choices=choices,
        )

        preply = self._build_preply_from_pform(pform, 'Reply#1')
        self._fill(preply, answer)

        return PollReplyLine.objects.get(pform_line=fline)

    def test_stats_rline_string(self):
        self.login()
        rline = self._build_rline_for_stat(PollLineType.STRING, 'a')
        self.assertEqual(None, rline.stats)

    def test_stats_rline_text(self):
        self.login()
        rline = self._build_rline_for_stat(PollLineType.TEXT, 'a')
        self.assertEqual(None, rline.stats)

    def test_stats_rline_integer(self):
        self.login()
        rline = self._build_rline_for_stat(PollLineType.INT, 12)
        self.assertEqual([(12, 1)], rline.stats)

    def test_stats_rline_boolean(self):
        self.login()
        rline = self._build_rline_for_stat(PollLineType.BOOL, 1)
        self.assertSetEqual({(_('Yes'), 1), (_('No'), 0)}, {*rline.stats})

    def test_stats_rline_boolean_false(self):
        self.login()
        rline = self._build_rline_for_stat(PollLineType.BOOL, 0)
        self.assertSetEqual({(_('Yes'), 0), (_('No'), 1)}, {*rline.stats})

    def test_stats_rline_enum(self):
        self.login()
        rline = self._build_rline_for_stat(
            PollLineType.ENUM, 1, [[1, 'European'], [2, 'African']],
        )
        self.assertSetEqual({('European', 1), ('African', 0)}, {*rline.stats})

    def test_stats_rline_multi_enum(self):
        self.login()
        rline = self._build_rline_for_stat(
            PollLineType.MULTI_ENUM, [2, 3],
            [[1, 'White'], [2, 'Black'], [3, 'Green'], [4, 'Purple']],
        )
        self.assertSetEqual(
            {('White', 0), ('Black', 1), ('Green', 1), ('Purple', 0)},
            {*rline.stats}
        )

    def test_stats_rline_enum_or_string(self):
        self.login()
        rline = self._build_rline_for_stat(
            PollLineType.ENUM_OR_STRING,
            {'answer_0': 0, 'answer_1': 'doh?'},
            [[1, 'White'], [2, 'Black'], [3, 'Green'], [4, 'Purple']],
        )
        self.assertSetEqual(
            {('White', 0), ('Black', 0), ('Green', 0), ('Purple', 0), (_('Other'), 1)},
            {*rline.stats},
        )

    def test_stats_rline_enum_or_string_custom(self):
        self.login()
        rline = self._build_rline_for_stat(
            PollLineType.ENUM_OR_STRING,
            {'answer_0': 2, 'answer_1': ''},
            [[1, 'White'], [2, 'Black'], [3, 'Green'], [4, 'Purple']],
        )
        self.assertSetEqual(
            {('White', 0), ('Black', 1), ('Green', 0), ('Purple', 0), (_('Other'), 0)},
            {*rline.stats},
        )

    def test_stats_rline_not_applicable(self):
        self.login()
        preply, rline = self._build_reply_with_bool_line()
        self._fill(preply, '', not_applicable=True)
        self.assertEqual([], self.refresh(rline).stats)

    def test_stats_tree(self):
        user = self.login()
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

        preply1 = self._build_preply_from_pform(pform, 'Reply#1')
        preply2 = self._build_preply_from_pform(pform, 'Reply#2')
        self._build_preply_from_pform(pform, 'Reply#3')  # No answer --> no stats
        preply4 = self._build_preply_from_pform(pform, 'Reply#4')

        answer_1_1 = 'They are cool'
        answer_2_1 = 5
        self._fill(
            preply1, answer_1_1, answer_2_1, 1, [1, 2], {'answer_0': 1, 'answer_1': ''},
        )

        answer_1_2 = 'They are very cool'
        self._fill(
            preply2, answer_1_2, answer_2_1, 2, [1], {'answer_0': 0, 'answer_1': 'Blue'},
        )

        answer_1_4 = 'They are very very cool'
        answer_2_4 = 10
        self._fill(
            preply4, answer_1_4, answer_2_4, 2, [1, 2, 4], {'answer_0': 0, 'answer_1': 'Red'},
        )

        with self.assertNumQueries(3):  # 1 for sections, 1 for lines, 1 for replies
            stree = StatsTree(pform)

        with self.assertNumQueries(0):
            nodes = [*stree]

        self.assertEqual([fline1, fline2, fline3, fline4, fline5], nodes)

        with self.assertNumQueries(0):
            stats1 = nodes[0].answer_stats
            stats2 = nodes[1].answer_stats
            stats3 = nodes[2].answer_stats
            stats4 = nodes[3].answer_stats
            stats5 = nodes[4].answer_stats

        self.assertFalse(stats1)
        self.assertSetEqual(
            {
                (answer_2_1, 2, round((2.0 * 100.0) / 3.0, 2)),
                (answer_2_4, 1, round((1.0 * 100.0) / 3.0, 2)),
            },
            {*stats2},
        )
        self.assertSetEqual(
            {
                ('European', 1, round((1.0 * 100.0) / 3.0, 2)),
                ('African',  2, round((2.0 * 100.0) / 3.0, 2)),
            },
            {*stats3},
        )
        self.assertSetEqual(
            {
                ('White',  3, round((3.0 * 100.0) / 6.0, 2)),
                ('Black',  2, round((2.0 * 100.0) / 6.0, 2)),
                ('Green',  0, 0.0),
                ('Purple', 1, round((1.0 * 100.0) / 6.0, 2)),
            },
            {*stats4},
        )
        self.assertSetEqual(
            {
                ('White',   1, round((1.0 * 100.0) / 3.0, 2)),
                ('Black',   0, 0.0),
                ('Green',   0, 0.0),
                ('Purple',  0, 0.0),
                (_('Other'), 2, round((2.0 * 100.0) / 3.0, 2)),
            },
            {*stats5},
        )

    def test_statsview(self):
        user = self.login()
        pform = PollForm.objects.create(user=user, name='Form#1')

        answer1 = 'African'
        answer2 = 'Sometimes'
        ENUM = PollLineType.ENUM
        create_line = self._get_formline_creator(pform)
        fline1 = create_line(
            'What type of swallow?',
            qtype=ENUM, choices=[[1, 'European'], [2, answer1]],
        )
        fline2 = create_line(
            'Do you eat swallows?',
            qtype=ENUM, choices=[[1, answer2], [2, 'Never']],
        )

        preply = self._build_preply_from_pform(pform, 'Reply#1')
        self._fill(preply, 2, 1)

        response = self.assertGET200(self._build_stats_url(pform))
        self.assertContains(response, fline1.question)
        self.assertContains(response, fline2.question)
        self.assertContains(response, answer1)
        self.assertContains(response, answer2)
