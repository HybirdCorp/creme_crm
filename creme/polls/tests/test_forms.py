from functools import partial
from json import dumps as json_dump

from django.forms import Field
from django.utils.translation import gettext as _

from creme.creme_core.tests.base import CremeTestCase

from ..core import PollLineType
from ..forms.fields import PollFormLineConditionsField
from ..models import PollFormLine, PollFormLineCondition
from .base import PollForm, skipIfCustomPollForm


class PollFormLineConditionsFieldTestCase(CremeTestCase):
    @staticmethod
    def build_data(*info):
        return json_dump([
            {'source': str(t['source']), 'choice': str(t['choice'])}
            for t in info
        ])

    def test_clean_empty_required(self):
        field = PollFormLineConditionsField()
        code = 'required'
        msg = Field.default_error_messages[code]
        self.assertFormfieldError(field=field, messages=msg, codes=code, value=None)
        self.assertFormfieldError(field=field, messages=msg, codes=code, value='')
        self.assertFormfieldError(field=field, messages=msg, codes=code, value=[])

    def test_clean_empty_not_required(self):
        field = PollFormLineConditionsField(required=False)
        self.assertNoException(field.clean, None)

    def test_clean_invalid_data_type(self):
        field = PollFormLineConditionsField()
        self.assertFormfieldError(
            field=field, value='[', codes='invalidformat', messages=_('Invalid format'),
        )

        type_code = 'invalidtype'
        type_msg = _('Invalid type')
        self.assertFormfieldError(
            field=field, messages=type_msg, codes=type_code, value='"this is a string"',
        )
        self.assertFormfieldError(
            field=field, messages=type_msg, codes=type_code, value='"{}"',
        )
        self.assertFormfieldError(
            field=field, codes=type_code, messages=type_msg,
            value='{"foobar":{"operator": "3", "name": "first_name"}}',
        )

    def _create_lines(self):
        user = self.get_root_user()
        self.pform = pform = PollForm.objects.create(user=user, name='Form#1')

        create_line = partial(PollFormLine.objects.create, pform=pform)
        serialize = PollLineType.build_serialized_args
        line1 = create_line(
            question='What is your favorite meal?',
            order=1, type=PollLineType.ENUM,
            type_args=serialize(
                ptype=PollLineType.ENUM,
                choices=[[1, 'Spam'], [2, 'Grilled swallow']],
            ),
        )
        line2 = create_line(
            question='What type of swallow have you already seen?',
            order=2,
            type=PollLineType.MULTI_ENUM,
            type_args=serialize(
                ptype=PollLineType.MULTI_ENUM,
                choices=[[1, 'European'], [2, 'African']],
            ),
        )

        return line1, line2

    @skipIfCustomPollForm
    def test_clean_invalid_source01(self):
        line1, line2 = self._create_lines()
        self.assertFormfieldError(
            field=PollFormLineConditionsField(sources=[line1]),
            value=self.build_data({'source': line2.id, 'choice': 1}),
            messages=_('This source is invalid.'),
            codes='invalidsource',
        )

    @skipIfCustomPollForm
    def test_clean_invalid_source02(self):
        "Only ENUM & MULTI_ENUM for now."
        line1, line2 = self._create_lines()
        line3 = PollFormLine.objects.create(
            pform=self.pform,
            question='What is your favorite meal?',
            type=PollLineType.STRING, order=3,
        )
        self.assertFormfieldError(
            field=PollFormLineConditionsField(sources=[line1, line2, line3]),
            value=self.build_data({'source': line3.id, 'choice': 1}),
            messages=_('This source is invalid.'),
            codes='invalidsource',
        )

    @skipIfCustomPollForm
    def test_clean_invalid_choice(self):
        line1, line2 = self._create_lines()
        self.assertFormfieldError(
            field=PollFormLineConditionsField(sources=[line1]),
            value=self.build_data({'source': line1.id, 'choice': 3}),
            codes='invalidchoice',
            messages=_('This choice is invalid.'),
        )

    @skipIfCustomPollForm
    def test_ok01(self):
        line1, line2 = self._create_lines()

        with self.assertNumQueries(0):
            field = PollFormLineConditionsField(sources=[line1, line2])

        condition = self.get_alone_element(
            field.clean(self.build_data({'source': line1.id, 'choice': 1}))
        )
        self.assertIsInstance(condition, PollFormLineCondition)
        self.assertIsNone(condition.pk)
        self.assertEqual(line1,                        condition.source)
        self.assertEqual(PollFormLineCondition.EQUALS, condition.operator)
        self.assertEqual('1',                          condition.raw_answer)

    @skipIfCustomPollForm
    def test_ok02(self):
        "Several conditions, sources property."
        line1, line2 = self._create_lines()

        with self.assertNumQueries(0):
            field = PollFormLineConditionsField()

        field.sources = [line1, line2]
        conditions = field.clean(self.build_data(
            {'source': line1.id, 'choice': 1},
            {'source': line2.id, 'choice': 2},
        ))
        self.assertEqual(2, len(conditions))

        condition = conditions[0]
        self.assertEqual(line1, condition.source)
        self.assertEqual('1',   condition.raw_answer)

        condition = conditions[1]
        self.assertEqual(line2, condition.source)
        self.assertEqual('[2]', condition.raw_answer)
