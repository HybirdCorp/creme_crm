from datetime import date, datetime, timedelta
from functools import partial

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core import mail
from django.db.models.query_utils import Q
from django.forms import ChoiceField, IntegerField, TypedChoiceField
from django.test.utils import override_settings
from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import gettext as _
from django.utils.translation import override as override_language

from creme.creme_core.core.entity_cell import (
    EntityCellFunctionField,
    EntityCellRegularField,
)
from creme.creme_core.core.function_field import function_field_registry
# Should be a test queue
from creme.creme_core.core.job import get_queue
from creme.creme_core.forms.fields import RelativeDatePeriodField
from creme.creme_core.forms.listview import TextLVSWidget
from creme.creme_core.models import (
    BrickDetailviewLocation,
    BrickHomeLocation,
    BrickState,
    CremeEntity,
    DateReminder,
    FakeContact,
    FakeOrganisation,
    FieldsConfig,
)
from creme.creme_core.tests.forms.base import FieldTestCase
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.creme_core.utils.date_period import (
    DatePeriodRegistry,
    DaysPeriod,
    HoursPeriod,
    MinutesPeriod,
    WeeksPeriod,
    YearsPeriod,
    date_period_registry,
)

from ..bricks import AlertsBrick
from ..constants import BRICK_STATE_HIDE_VALIDATED_ALERTS
from ..forms.alert import (
    AbsoluteOrRelativeDatetimeField,
    ModelRelativeDatePeriodField,
    ModelRelativeDatePeriodWidget,
)
from ..models import Alert
from .base import AssistantsTestCase


class ModelRelativeDatePeriodWidgetTestCase(AssistantsTestCase):
    @override_language('en')
    def test_render_en_no_value(self):
        name = 'date_period'
        self.maxDiff = None
        self.assertHTMLEqual(
            f'<ul class="hbox ui-layout">'
            f' <li>'
            f'  <input class="assistants-offset_dperiod-value" min="1"'
            f'         name="{name}_3" type="number">'
            f' </li>'
            f' <li>'
            f'  <div class="select-wrapper">'
            f'   <select class="assistants-offset_dperiod-type" name="{name}_2" />'
            f'   <div class="select-arrow" />'
            f'  </div>'
            f' </li>'
            f' <li>'
            f'  <div class="select-wrapper">'
            f'   <select class="assistants-offset_dperiod-direction" name="{name}_1" />'
            f'   <div class="select-arrow" />'
            f' </li>'
            f' <li>'
            f'  <div class="select-wrapper">'
            f'   <select class="assistants-offset_dperiod-field" name="{name}_0" />'
            f'   <div class="select-arrow" />'
            f'  </div>'
            f' </li>'
            f'</ul>',
            ModelRelativeDatePeriodWidget().render(name=name, value=None),
        )

    @override_language('en')
    def test_render_en_list_value(self):
        name = 'offset'
        widget = ModelRelativeDatePeriodWidget()
        widget.period_choices = [
            (period.name, period.verbose_name) for period in [
                HoursPeriod,
                DaysPeriod,
                WeeksPeriod,
            ]
        ]
        widget.relative_choices = [(-1, 'Before'), (1, 'After')]
        widget.field_choices = [('created', 'Created'), ('modified', 'Modified')]
        self.maxDiff = None
        self.assertHTMLEqual(
            f'<ul class="hbox ui-layout">'
            f' <li>'
            f'  <input class="assistants-offset_dperiod-value" min="1"'
            f'         name="{name}_3" type="number" value="5">'
            f' </li>'
            f' <li>'
            f'  <div class="select-wrapper">'
            f'   <select class="assistants-offset_dperiod-type" name="{name}_2">'
            f'    <option value="hours">Hour(s)</option>'
            f'    <option value="days">Day(s)</option>'
            f'    <option value="weeks" selected>Week(s)</option>'
            f'   </select>'
            f'   <div class="select-arrow" />'
            f'  </div>'
            f' </li>'
            f' <li>'
            f'  <div class="select-wrapper">'
            f'   <select class="assistants-offset_dperiod-direction" name="{name}_1">'
            f'    <option value="-1">Before</option>'
            f'    <option value="1" selected>After</option>'
            f'   </select>'
            f'   <div class="select-arrow" />'
            f' </li>'
            f' <li>'
            f'  <div class="select-wrapper">'
            f'   <select class="assistants-offset_dperiod-field" name="{name}_0">'
            f'    <option value="created">Created</option>'
            f'    <option value="modified" selected>Modified</option>'
            f'   </select>'
            f'   <div class="select-arrow" />'
            f'  </div>'
            f' </li>'
            f'</ul>',
            widget.render(name=name, value=['modified', ['1', [WeeksPeriod.name, '5']]]),
        )

    @override_language('fr')
    def test_render_fr(self):
        name = 'date_offset'
        widget = ModelRelativeDatePeriodWidget()
        widget.period_choices = [
            (period.name, period.verbose_name) for period in [
                HoursPeriod,
                DaysPeriod,
                WeeksPeriod,
            ]
        ]
        widget.relative_choices = [(-1, 'Avant'), (1, 'Après')]
        widget.field_choices = [
            ('created', 'Création'),
            ('modified', 'Modification'),
            ('birthday', 'Anniversaire'),
        ]
        self.maxDiff = None
        self.assertHTMLEqual(
            f'<ul class="hbox ui-layout">'
            f' <li>'
            f'  <input class="assistants-offset_dperiod-value" min="1"'
            f'         name="{name}_3" type="number" value="2">'
            f' </li>'
            f' <li>'
            f'  <div class="select-wrapper">'
            f'   <select class="assistants-offset_dperiod-type" name="{name}_2">'
            f'    <option value="hours">Heure(s)</option>'
            f'    <option value="days" selected>Jour(s)</option>'
            f'    <option value="weeks">Semaine(s)</option>'
            f'   </select>'
            f'   <div class="select-arrow" />'
            f'  </div>'
            f' </li>'
            f' <li>'
            f'  <div class="select-wrapper">'
            f'   <select class="assistants-offset_dperiod-direction" name="{name}_1">'
            f'    <option value="-1">Avant</option>'
            f'    <option value="1" selected>Après</option>'
            f'   </select>'
            f'   <div class="select-arrow" />'
            f' </li>'
            f' <li>'
            f'  <div class="select-wrapper">'
            f'   <select class="assistants-offset_dperiod-field" name="{name}_0">'
            f'    <option value="created">Création</option>'
            f'    <option value="modified">Modification</option>'
            f'    <option value="birthday" selected>Anniversaire</option>'
            f'   </select>'
            f'   <div class="select-arrow" />'
            f'  </div>'
            f' </li>'
            f'</ul>',
            widget.render(
                name=name,
                value=ModelRelativeDatePeriodField.ModelRelativeDatePeriod(
                    field_name='birthday',
                    relative_period=RelativeDatePeriodField.RelativeDatePeriod(
                        sign=1, period=DaysPeriod(2),
                    ),
                ),
            ),
        )

    def test_value_from_datadict(self):
        self.assertListEqual(
            ['created', ['-1', ['hours', '5']]],
            ModelRelativeDatePeriodWidget().value_from_datadict(
                name='offset',
                data={
                    'offset_0': 'created',
                    'offset_1': '-1',
                    'offset_2': 'hours',
                    'offset_3': '5',
                    'whatever': 'foo',
                },
                files={},
            ),
        )


class ModelRelativeDatePeriodFieldTestCase(FieldTestCase):
    def test_model_relativedate_period(self):
        RPeriod = RelativeDatePeriodField.RelativeDatePeriod
        MRPeriod = ModelRelativeDatePeriodField.ModelRelativeDatePeriod

        mrperiod1 = MRPeriod(
            field_name='modified',
            relative_period=RPeriod(sign=1, period=DaysPeriod(1)),
        )
        self.assertEqual('modified', mrperiod1.field_name)
        self.assertEqual(
            RPeriod(sign=1, period=DaysPeriod(1)),
            mrperiod1.relative_period,
        )

        mrperiod2 = MRPeriod(
            field_name='created',
            relative_period=RPeriod(sign=-1, period=WeeksPeriod(2)),
        )
        self.assertEqual('created', mrperiod2.field_name)
        self.assertEqual(
            RPeriod(sign=-1, period=WeeksPeriod(2)),
            mrperiod2.relative_period,
        )

        self.assertNotEqual(None, mrperiod1)
        self.assertNotEqual(mrperiod1, mrperiod2)
        self.assertNotEqual(
            MRPeriod(
                field_name='created',
                relative_period=RPeriod(sign=1, period=DaysPeriod(1)),
            ),
            mrperiod1,
        )
        self.assertNotEqual(
            MRPeriod(
                field_name='modified',
                relative_period=RPeriod(sign=1, period=DaysPeriod(2)),
            ),
            mrperiod1,
        )
        self.assertEqual(
            MRPeriod(
                field_name='modified',
                relative_period=RPeriod(sign=1, period=DaysPeriod(1)),
            ),
            mrperiod1,
        )

    def test_ok01(self):
        "Field <FakeOrganisation.creation_date> + days + after."
        field_name = 'creation_date'
        offset = ModelRelativeDatePeriodField(model=FakeOrganisation).clean(
            # [field_name, '1', DaysPeriod.name, '3'],
            [field_name, ['1', [DaysPeriod.name, '3']]],
        )
        # self.assertIsTuple(offset, length=2)
        # self.assertEqual(field_name, offset[0])
        #
        # signed_period = offset[1]
        # self.assertIsTuple(signed_period, length=2)
        # self.assertEqual(1, signed_period[0])
        #
        # period = signed_period[1]
        # self.assertIsInstance(period, DaysPeriod)
        # self.assertDictEqual({'type': 'days', 'value': 3}, period.as_dict())
        self.assertEqual(
            ModelRelativeDatePeriodField.ModelRelativeDatePeriod(
                field_name=field_name,
                relative_period=RelativeDatePeriodField.RelativeDatePeriod(
                    sign=1, period=DaysPeriod(3),
                ),
            ),
            offset,
        )

    def test_ok02(self):
        "Field <FakeOrganisation.created> + minutes + before."
        field_name = 'created'
        offset = ModelRelativeDatePeriodField(model=FakeOrganisation).clean(
            # [field_name, '-1', MinutesPeriod.name, '5']
            [field_name, ['-1', [MinutesPeriod.name, '5']]]
        )
        # self.assertEqual(field_name, offset[0])
        #
        # sign, period = offset[1]
        # self.assertEqual(-1, sign)
        # self.assertIsInstance(period, MinutesPeriod)
        # self.assertDictEqual({'type': 'minutes', 'value': 5}, period.as_dict())
        self.assertEqual(
            ModelRelativeDatePeriodField.ModelRelativeDatePeriod(
                field_name=field_name,
                relative_period=RelativeDatePeriodField.RelativeDatePeriod(
                    sign=-1, period=MinutesPeriod(5),
                ),
            ),
            offset,
        )

    def test_required(self):
        cls = ModelRelativeDatePeriodField
        field = cls(model=FakeOrganisation)
        clean = field.clean
        pname = DaysPeriod.name
        # self.assertFieldValidationError(cls, 'required', clean, ['', '', '', ''])
        # self.assertFieldValidationError(cls, 'required', clean, None)
        # self.assertFieldValidationError(cls, 'required', clean, ['', '', pname, '2'])
        # self.assertFieldValidationError(cls, 'required', clean, ['', '1', pname, ''])
        # self.assertFieldValidationError(cls, 'required', clean, ['created', '1', pname, ''])
        self.assertFieldValidationError(cls, 'required', clean, ['', ['', ['', '']]])
        self.assertFieldValidationError(cls, 'required', clean, None)
        self.assertFieldValidationError(cls, 'required', clean, ['', ['', [pname, '2']]])
        self.assertFieldValidationError(cls, 'required', clean, ['', ['1', [pname, '']]])
        self.assertFieldValidationError(cls, 'required', clean, ['created', ['1', [pname, '']]])

    def test_not_required(self):
        clean = ModelRelativeDatePeriodField(required=False).clean
        # empty = ()
        # self.assertTupleEqual(empty, clean([''] * 4))
        # self.assertTupleEqual(empty, clean([''] * 3))
        # self.assertTupleEqual(empty, clean([''] * 2))
        # self.assertTupleEqual(empty, clean(['']))
        # self.assertTupleEqual(empty, clean([]))
        # self.assertTupleEqual(empty, clean(None))
        # self.assertTupleEqual(empty, clean(['created', '1', DaysPeriod.name, '']))
        # self.assertTupleEqual(empty, clean(['', '1', '', '2']))
        self.assertIsNone(clean([''] * 4))
        self.assertIsNone(clean([''] * 3))
        self.assertIsNone(clean([''] * 2))
        self.assertIsNone(clean(['']))
        self.assertIsNone(clean([]))
        self.assertIsNone(clean(None))
        self.assertIsNone(clean(['created', ['1', [DaysPeriod.name, '']]]))
        self.assertIsNone(clean(['', ['1', ['', '2']]]))

    def test_invalid(self):
        clean = ModelRelativeDatePeriodField(model=FakeOrganisation).clean

        f_name = 'invalid_field'
        self.assertFieldValidationError(
            ChoiceField, 'invalid_choice', clean,
            # [f_name, '-1', YearsPeriod.name, '5'],
            [f_name, ['-1', [YearsPeriod.name, '5']]],
            message_args={'value': f_name},
        )

        self.assertFieldValidationError(
            TypedChoiceField, 'invalid_choice', clean,
            # ['created', 'notint', YearsPeriod.name, '1'],
            ['created', ['notint', [YearsPeriod.name, '1']]],
            message_args={'value': 'notint'},
        )
        self.assertFieldValidationError(
            IntegerField, 'invalid', clean,
            # ['created', '1', YearsPeriod.name, 'notint'],
            ['created', ['1', [YearsPeriod.name, 'notint']]],
        )

        p_name = 'unknownperiod'
        self.assertFieldValidationError(
            # ChoiceField, 'invalid_choice', clean, ['created', '-1', p_name, '2'],
            ChoiceField, 'invalid_choice', clean, ['created', ['-1', [p_name, '2']]],
            message_args={'value': p_name},
        )

    def test_model_1(self):
        "Constructor argument."
        field = ModelRelativeDatePeriodField(model=FakeOrganisation)
        self.assertEqual(FakeOrganisation, field.model)

        choices = field.fields[0].choices
        self.assertInChoices(value='created',       label=_('Creation date'),     choices=choices)
        self.assertInChoices(value='modified',      label=_('Last modification'), choices=choices)
        self.assertInChoices(value='creation_date', label=_('Date of creation'),  choices=choices)
        self.assertNotInChoices(value='name', choices=choices)

        self.assertListEqual([*choices], [*field.widget.field_choices])

    def test_model_2(self):
        "Property."
        field = ModelRelativeDatePeriodField()
        self.assertEqual(CremeEntity, field.model)

        choices1 = field.fields[0].choices
        self.assertInChoices(value='created', label=_('Creation date'), choices=choices1)
        self.assertNotInChoices(value='creation_date', choices=choices1)

        field.model = FakeOrganisation
        choices2 = field.fields[0].choices
        self.assertInChoices(value='created',       label=_('Creation date'),    choices=choices2)
        self.assertInChoices(value='creation_date', label=_('Date of creation'), choices=choices2)

    def test_model_3(self):
        "With FieldsConfig."
        model = FakeContact
        hidden = 'birthday'
        FieldsConfig.objects.create(
            content_type=model,
            descriptions=[(hidden, {FieldsConfig.HIDDEN: True})],
        )

        field = ModelRelativeDatePeriodField(model=model)
        choices = field.fields[0].choices
        self.assertInChoices(value='created', label=_('Creation date'), choices=choices)
        self.assertNotInChoices(value=hidden, choices=choices)

        # TODO: validation error?

    def test_model_4(self):
        "With FieldsConfig but field1 is already selected => still proposed."
        model = FakeContact
        hidden = 'birthday'
        FieldsConfig.objects.create(
            content_type=model,
            descriptions=[(hidden, {FieldsConfig.HIDDEN: True})],
        )

        non_hiddable_cell = EntityCellRegularField.build(model, hidden)

        # Property setter ------------------------------------------------------
        field1 = ModelRelativeDatePeriodField(model=model)
        self.assertIsNone(field1.non_hiddable_cell)
        field1.non_hiddable_cell = non_hiddable_cell
        self.assertEqual(non_hiddable_cell, field1.non_hiddable_cell)

        choices1 = field1.fields[0].choices
        self.assertInChoices(value='created', label=_('Creation date'), choices=choices1)
        self.assertInChoices(value=hidden,    label=_('Birthday'),      choices=choices1)

        # Constructor ----------------------------------------------------------
        field2 = ModelRelativeDatePeriodField(model=model, non_hiddable_cell=non_hiddable_cell)
        self.assertListEqual([*choices1], [*field2.fields[0].choices])

    def test_non_hiddable_cell_errors(self):
        model = FakeContact
        field = ModelRelativeDatePeriodField(model=model)

        with self.assertRaises(ValueError):
            field.non_hiddable_cell = EntityCellFunctionField.build(
                model, 'get_pretty_properties',
            )

        with self.assertRaises(ValueError):
            field.non_hiddable_cell = EntityCellRegularField.build(FakeOrganisation, 'created')

        with self.assertRaises(ValueError):
            field.non_hiddable_cell = EntityCellRegularField.build(model, 'image__created')

        with self.assertRaises(ValueError):
            field.non_hiddable_cell = EntityCellRegularField.build(model, 'first_name')

    def test_period_names_1(self):
        "Constructor argument."
        names = (MinutesPeriod.name, HoursPeriod.name)
        field = ModelRelativeDatePeriodField(model=FakeContact, period_names=names)
        self.assertEqual(names, field.fields[1].period_names)
        self.assertEqual(names, field.period_names)
        self.assertListEqual(
            [*date_period_registry.choices(choices=names)],
            [*field.widget.period_choices],
        )

    def test_period_names_2(self):
        "Property."
        field = ModelRelativeDatePeriodField(model=FakeContact)
        field.period_names = names = (MinutesPeriod.name, HoursPeriod.name)
        self.assertEqual(names, field.fields[1].period_names)
        self.assertListEqual(
            [*date_period_registry.choices(choices=names)],
            [*field.widget.period_choices],
        )

    def test_registry_1(self):
        field = ModelRelativeDatePeriodField(model=FakeContact)
        self.assertEqual(date_period_registry, field.period_registry)
        self.assertListEqual(
            [*date_period_registry.choices()],
            [*field.widget.period_choices],
        )

    def test_registry_2(self):
        registry = DatePeriodRegistry(MinutesPeriod, HoursPeriod)
        field = ModelRelativeDatePeriodField(
            model=FakeContact, period_registry=registry,
        )
        self.assertEqual(registry, field.period_registry)
        self.assertListEqual([*registry.choices()], [*field.widget.period_choices])

    def test_registry_3(self):
        "Property setter."
        registry = DatePeriodRegistry(MinutesPeriod, HoursPeriod)
        field = ModelRelativeDatePeriodField(model=FakeContact)
        field.period_registry = registry
        self.assertEqual(registry, field.period_registry)
        self.assertListEqual([*registry.choices()], [*field.widget.period_choices])

    def test_relative_choices_1(self):
        "Default choices."
        field = ModelRelativeDatePeriodField(model=FakeContact)
        expected_choices = [(-1, _('Before')), (1, _('After'))]
        self.assertListEqual(expected_choices, [*field.fields[1].relative_choices])
        self.assertListEqual(expected_choices, [*field.relative_choices])
        self.assertListEqual(expected_choices, [*field.widget.relative_choices])

    def test_relative_choices_2(self):
        "Property."
        field = ModelRelativeDatePeriodField(model=FakeContact)
        choices = [(-1, 'In the past'), (1, 'In the future')]
        field.relative_choices = choices
        self.assertListEqual(choices, [*field.fields[1].relative_choices])
        self.assertListEqual(choices, [*field.widget.relative_choices])


class AbsoluteOrRelativeDatetimeFieldTestCase(FieldTestCase):
    def test_ok(self):
        field = AbsoluteOrRelativeDatetimeField(model=FakeOrganisation)
        self.assertEqual(FakeOrganisation, field.model)

        ABSOLUTE = AbsoluteOrRelativeDatetimeField.ABSOLUTE
        RELATIVE = AbsoluteOrRelativeDatetimeField.RELATIVE
        dt_kwargs = {'year': 2022, 'month': 5, 'day': 9, 'hour': 16, 'minute': 30}
        field_name = 'creation_date'
        sub_values = {
            ABSOLUTE: self.formfield_value_datetime(**dt_kwargs),
            # RELATIVE: [field_name, '1', DaysPeriod.name, '3'],
            RELATIVE: [field_name, ['1', [DaysPeriod.name, '3']]],
        }
        self.assertTupleEqual(
            (ABSOLUTE, self.create_datetime(**dt_kwargs)),
            field.clean((ABSOLUTE, sub_values)),
        )

        # ---
        cleaned2 = field.clean((RELATIVE, sub_values))
        self.assertIsTuple(cleaned2, length=2)
        self.assertEqual(RELATIVE, cleaned2[0])

        # offset = cleaned2[1]
        # self.assertIsTuple(offset, length=2)
        # self.assertEqual(field_name, offset[0])
        #
        # signed_period = offset[1]
        # self.assertIsTuple(signed_period, length=2)
        # self.assertEqual(1, signed_period[0])
        #
        # period = signed_period[1]
        # self.assertIsInstance(period, DaysPeriod)
        # self.assertDictEqual({'type': 'days', 'value': 3}, period.as_dict())
        self.assertEqual(
            ModelRelativeDatePeriodField.ModelRelativeDatePeriod(
                field_name=field_name,
                relative_period=RelativeDatePeriodField.RelativeDatePeriod(
                    sign=1, period=DaysPeriod(3),
                ),
            ),
            cleaned2[1],
        )

    def test_non_hiddable_cell(self):
        model = FakeOrganisation
        field = AbsoluteOrRelativeDatetimeField(model=model)
        self.assertIsNone(field.non_hiddable_cell)

        field.non_hiddable_cell = cell = EntityCellRegularField.build(model, 'creation_date')
        self.assertEqual(cell, field.non_hiddable_cell)
        self.assertEqual(cell, field.fields_choices[1][1].non_hiddable_cell)


class AlertTestCase(BrickTestCaseMixin, AssistantsTestCase):
    @staticmethod
    def _build_add_url(entity):
        return reverse('assistants__create_alert', args=(entity.id,))

    def _create_alert(self,
                      title='TITLE',
                      description='DESCRIPTION',
                      # trigger_date='2010-9-29',
                      trigger_date=datetime(year=2010, month=9, day=29, hour=8),
                      entity=None,
                      ):
        entity = entity or self.entity

        ABSOLUTE = AbsoluteOrRelativeDatetimeField.ABSOLUTE
        response = self.client.post(
            self._build_add_url(entity),
            data={
                'user':         self.user.pk,
                'title':        title,
                'description':  description,
                # 'trigger_date': trigger_date,

                'trigger': ABSOLUTE,
                f'trigger_{ABSOLUTE}': self.formfield_value_datetime(trigger_date),
            },
        )
        self.assertNoFormError(response)

        return self.get_object_or_fail(Alert, title=title, description=description)

    def test_create_with_absolute_date(self):
        self.assertFalse(Alert.objects.exists())

        entity = self.entity
        entity.user = self.other_user
        entity.save()

        queue = get_queue()
        queue.clear()

        entity = self.entity
        context = self.assertGET200(self._build_add_url(entity)).context
        self.assertEqual(
            _('New alert for «{entity}»').format(entity=entity),
            context.get('title'),
        )
        self.assertEqual(_('Save the alert'), context.get('submit_label'))

        with self.assertNoException():
            fields = context['form'].fields
            user_f = fields['user']
            trigger_f = fields['trigger']

        self.assertFalse(user_f.required)
        self.assertEqual(
            _('Same owner than the entity (currently «{user}»)').format(user=self.other_user),
            user_f.empty_label,
        )

        self.assertTupleEqual(
            (AbsoluteOrRelativeDatetimeField.ABSOLUTE, {}),
            trigger_f.initial,
        )
        self.assertEqual(type(entity), trigger_f.model)
        self.assertIsNone(trigger_f.non_hiddable_cell)

        # ---
        title = 'Title'
        # alert = self._create_alert(title, 'Description', '2010-9-29')
        dt_kwargs = {'year': 2010, 'month': 9, 'day': 29, 'hour': 8, 'minute': 0}
        alert = self._create_alert(title, 'Description', datetime(**dt_kwargs))
        self.assertEqual(1, Alert.objects.count())

        self.assertIs(False,        alert.is_validated)
        self.assertEqual(self.user, alert.user)
        self.assertIs(False,        alert.reminded)

        self.assertEqual(entity.id,             alert.entity_id)
        self.assertEqual(entity.entity_type_id, alert.entity_content_type_id)
        self.assertEqual(
            # self.create_datetime(year=2010, month=9, day=29),
            self.create_datetime(**dt_kwargs),
            alert.trigger_date,
        )
        self.assertDictEqual({}, alert.trigger_offset)

        self.assertEqual(title, str(alert))

        jobs = queue.refreshed_jobs
        self.assertEqual(1, len(jobs))
        self.assertEqual(self.get_reminder_job(), jobs[0][0])

    def test_create_with_relative_datetime(self):
        "DatetimeField + dynamic user."
        entity = self.entity

        RELATIVE = AbsoluteOrRelativeDatetimeField.RELATIVE
        title = 'My alert'
        days = 12
        field_name = 'created'
        response = self.client.post(
            self._build_add_url(entity),
            data={
                # 'user':         self.user.pk,
                'title':        title,
                'description':  '',

                'trigger': RELATIVE,
                f'trigger_{RELATIVE}_0': field_name,
                f'trigger_{RELATIVE}_1': '1',
                f'trigger_{RELATIVE}_2': DaysPeriod.name,
                f'trigger_{RELATIVE}_3': str(days),
            },
        )
        self.assertNoFormError(response)

        alert = self.get_object_or_fail(Alert, title=title, description='')
        self.assertIsNone(alert.user)
        self.assertEqual(alert.trigger_date, entity.created + timedelta(days=days))
        self.assertDictEqual(
            {
                'cell': {'type': 'regular_field', 'value': field_name},
                'sign': 1,
                'period': {'type': DaysPeriod.name, 'value': days},
            },
            alert.trigger_offset,
        )

    def test_create_with_relative_date(self):
        "DateField + not in CremeEntity, in the past."
        entity = self.entity
        entity.birthday = date(year=2000, month=3, day=12)
        entity.save()

        RELATIVE = AbsoluteOrRelativeDatetimeField.RELATIVE
        title = 'My alert'
        field_name = 'birthday'
        weeks = 1
        response = self.client.post(
            self._build_add_url(entity),
            data={
                'user':         self.user.pk,
                'title':        title,
                'description':  '',

                'trigger': RELATIVE,
                f'trigger_{RELATIVE}_0': field_name,
                f'trigger_{RELATIVE}_1': '-1',
                f'trigger_{RELATIVE}_2': WeeksPeriod.name,
                f'trigger_{RELATIVE}_3': str(weeks),
            },
        )
        self.assertNoFormError(response)

        alert = self.get_object_or_fail(Alert, title=title, description='')
        self.assertEqual(
            self.create_datetime(year=2000, month=3, day=5),
            alert.trigger_date,
        )
        self.assertDictEqual(
            {
                'cell': {'type': 'regular_field', 'value': field_name},
                'sign': -1,
                'period': {'type': WeeksPeriod.name, 'value': weeks},
            },
            alert.trigger_offset,
        )

    def test_create_errors(self):
        def _fail_creation(**post_data):
            response = self.assertPOST200(self._build_add_url(self.entity), data=post_data)

            with self.assertNoException():
                form = response.context['form']

            self.assertFalse(form.is_valid(), f'Creation should fail with data={post_data}')

        user_pk = self.user.pk
        ABSOLUTE = AbsoluteOrRelativeDatetimeField.ABSOLUTE
        _fail_creation(
            user=user_pk, description='description',
            title='',  # <==
            # trigger_date='2010-9-29',
            # trigger_date=self.formfield_value_date(2010, 9, 29),
            **{
                'trigger': ABSOLUTE,
                f'trigger_{ABSOLUTE}': self.formfield_value_datetime(year=2010, month=9, day=29),
            }
        )
        _fail_creation(
            user=user_pk, title='title', description='description',
            # trigger_date='',  # <===
            trigger='',  # <===
        )

    # def test_edit(self):
    def test_edit_absolute_date(self):
        title = 'Title'
        description = 'Description'
        # alert = self._create_alert(title, description, '2010-9-29')
        alert = self._create_alert(title, description)

        url = alert.get_edit_absolute_url()
        context = self.assertGET200(url).context
        self.assertEqual(
            _('Alert for «{entity}»').format(entity=self.entity),
            context.get('title'),
        )

        with self.assertNoException():
            trigger_f = context['form'].fields['trigger']

        ABSOLUTE = AbsoluteOrRelativeDatetimeField.ABSOLUTE
        self.assertTupleEqual(
            (ABSOLUTE, {ABSOLUTE: alert.trigger_date}),
            trigger_f.initial,
        )

        # ---
        title += '_edited'
        description += '_edited'
        dt_kwargs = {'year': 2011, 'month': 10, 'day': 30, 'hour': 15, 'minute': 12}
        response = self.client.post(
            url,
            data={
                'user':         self.user.pk,
                'title':        title,
                'description':  description,

                # 'trigger_date': '2011-10-30',
                # 'trigger_time': '15:12:00',
                'trigger': ABSOLUTE,
                f'trigger_{ABSOLUTE}': self.formfield_value_datetime(**dt_kwargs),
            },
        )
        self.assertNoFormError(response)

        alert = self.refresh(alert)
        self.assertEqual(title,       alert.title)
        self.assertEqual(description, alert.description)

        # Don't care about seconds
        self.assertEqual(
            # self.create_datetime(year=2011, month=10, day=30, hour=15, minute=12),
            self.create_datetime(**dt_kwargs),
            alert.trigger_date,
        )

    def test_edit_relative_date01(self):
        entity = self.entity
        entity.birthday = date(year=2000, month=6, day=25)
        entity.save()

        field_name = 'birthday'
        alert = Alert.objects.create(
            user=self.user,
            real_entity=entity,
            title='Title',
            trigger_date=self.create_datetime(
                year=2000, month=6, day=24, hour=0, minute=0,
            ),
            trigger_offset={
                'cell': {'type': 'regular_field', 'value': field_name},
                'sign': -1,
                'period': {'type': DaysPeriod.name, 'value': 1},
            },
        )

        url = alert.get_edit_absolute_url()
        response1 = self.client.get(url)

        with self.assertNoException():
            trigger_f = response1.context['form'].fields['trigger']

        RELATIVE = AbsoluteOrRelativeDatetimeField.RELATIVE
        self.assertTupleEqual(
            (
                RELATIVE,
                # {RELATIVE: (field_name, -1, DaysPeriod(1))},
                {
                    RELATIVE: ModelRelativeDatePeriodField.ModelRelativeDatePeriod(
                        field_name=field_name,
                        relative_period=RelativeDatePeriodField.RelativeDatePeriod(
                            sign=-1, period=DaysPeriod(1),
                        ),
                    ),
                },
            ),
            trigger_f.initial,
        )
        self.assertEqual(
            EntityCellRegularField.build(model=type(entity), name=field_name),
            trigger_f.non_hiddable_cell,
        )

        # ---
        title = f'{alert.title} (edited)'
        weeks = 2
        response2 = self.client.post(
            url,
            data={
                'user':         self.user.pk,
                'title':        title,
                'description':  alert.description,

                'trigger': RELATIVE,
                f'trigger_{RELATIVE}_0': field_name,
                f'trigger_{RELATIVE}_1': '-1',
                f'trigger_{RELATIVE}_2': WeeksPeriod.name,
                f'trigger_{RELATIVE}_3': str(weeks),
            },
        )
        self.assertNoFormError(response2)

        alert = self.refresh(alert)
        self.assertEqual(title, alert.title)
        self.assertEqual(
            self.create_datetime(year=2000, month=6, day=11, hour=0, minute=0),
            alert.trigger_date,
        )
        self.assertDictEqual(
            {
                'cell': {'type': 'regular_field', 'value': field_name},
                'sign': -1,
                'period': {'type': WeeksPeriod.name, 'value': weeks},
            },
            alert.trigger_offset,
        )

    def test_edit_relative_date02(self):
        "NULL date."
        entity = self.entity
        self.assertIsNone(entity.birthday)

        field_name = 'birthday'
        alert = self._create_alert(title='My alert #1')

        RELATIVE = AbsoluteOrRelativeDatetimeField.RELATIVE
        weeks = 1
        response = self.client.post(
            alert.get_edit_absolute_url(),
            data={
                'user':         self.user.pk,
                'title':        alert.title,
                'description':  alert.description,

                'trigger': RELATIVE,
                f'trigger_{RELATIVE}_0': field_name,
                f'trigger_{RELATIVE}_1': '-1',
                f'trigger_{RELATIVE}_2': WeeksPeriod.name,
                f'trigger_{RELATIVE}_3': str(weeks),
            },
        )
        self.assertNoFormError(response)

        alert = self.refresh(alert)
        self.assertIsNone(alert.trigger_date)
        self.assertDictEqual(
            {
                'cell': {'type': 'regular_field', 'value': field_name},
                'sign': -1,
                'period': {'type': WeeksPeriod.name, 'value': weeks},
            },
            alert.trigger_offset,
        )

    def test_edit_relative_date03(self):
        "Change to absolute => empty offset."
        field_name = 'birthday'
        alert = Alert.objects.create(
            user=self.user,
            real_entity=self.entity,
            title='Title',
            trigger_date=self.create_datetime(
                year=2022, month=5, day=10, hour=0, minute=0,
            ),
            trigger_offset={
                'cell': {'type': 'regular_field', 'value': field_name},
                'sign': -1,
                'period': {'type': DaysPeriod.name, 'value': 1},
            },
        )

        title = f'{alert.title} (edited)'
        ABSOLUTE = AbsoluteOrRelativeDatetimeField.ABSOLUTE
        dt_kwargs = {'year': 2022, 'month': 5, 'day': 10, 'hour': 15, 'minute': 30}
        response = self.client.post(
            alert.get_edit_absolute_url(),
            data={
                'user':  self.user.pk,
                'title': title,

                'trigger': ABSOLUTE,
                f'trigger_{ABSOLUTE}': self.formfield_value_datetime(**dt_kwargs),
            },
        )
        self.assertNoFormError(response)

        alert = self.refresh(alert)
        self.assertEqual(self.create_datetime(**dt_kwargs), alert.trigger_date)
        self.assertDictEqual({}, alert.trigger_offset)

    def test_delete_related01(self):
        self._create_alert()
        self.assertEqual(1, Alert.objects.count())

        self.entity.delete()
        self.assertEqual(0, Alert.objects.count())

    def test_delete01(self):
        alert = self._create_alert()
        self.assertEqual(1, Alert.objects.count())

        ct = ContentType.objects.get_for_model(Alert)
        self.client.post(
            reverse('creme_core__delete_related_to_entity', args=(ct.id,)),
            data={'id': alert.id},
        )
        self.assertFalse(Alert.objects.all())

    def test_validate(self):
        alert = self._create_alert()
        self.assertFalse(alert.is_validated)

        url = reverse('assistants__validate_alert', args=(alert.id,))
        self.assertGET405(url)

        response = self.assertPOST200(url, follow=True)
        self.assertRedirects(response, self.entity.get_absolute_url())

        self.assertTrue(self.refresh(alert).is_validated)

    def test_offset_signal01(self):
        entity = self.entity
        alert = Alert.objects.create(
            user=self.user,
            real_entity=self.entity,
            title='Title',
            trigger_date=self.create_datetime(
                year=2022, month=5, day=10, hour=0, minute=0,
            ),
            trigger_offset={
                'cell': {'type': 'regular_field', 'value': 'modified'},
                'sign': 1,
                'period': {'type': DaysPeriod.name, 'value': 1},
            },
        )

        entity.phone = '11 22 33'
        entity.save()  # NB: the field 'modified' is updated
        self.assertDatetimesAlmostEqual(
            entity.modified + relativedelta(days=1),
            self.refresh(alert).trigger_date,
        )

    def test_offset_signal02(self):
        """date == NULL."""
        entity = self.entity
        entity.birthday = date(year=1980, month=2, day=15)
        entity.save()

        alert = Alert.objects.create(
            user=self.user,
            real_entity=self.entity,
            title='Title',
            trigger_date=self.create_datetime(
                year=1980, month=2, day=25, hour=0, minute=0,
            ),
            trigger_offset={
                'cell': {'type': 'regular_field', 'value': 'birthday'},
                'sign': 1,
                'period': {'type': DaysPeriod.name, 'value': 10},
            },
        )

        entity.birthday = None
        entity.save()
        self.assertIsNone(self.refresh(alert).trigger_date)

    def test_offset_signal03(self):
        """Validated alerts are not updated."""
        entity = self.entity
        trigger_date = self.create_datetime(
            year=2022, month=5, day=10, hour=0, minute=0,
        )
        alert = Alert.objects.create(
            user=self.user,
            real_entity=self.entity,
            title='Title',
            trigger_date=trigger_date,
            trigger_offset={
                'cell': {'type': 'regular_field', 'value': 'modified'},
                'sign': 1,
                'period': {'type': DaysPeriod.name, 'value': 1},
            },
            is_validated=True,
        )

        entity.phone = '11 22 33'
        entity.save()  # NB: the field 'modified' is updated
        self.assertEqual(trigger_date, self.refresh(alert).trigger_date)

    def test_function_field01(self):
        funf = function_field_registry.get(CremeEntity, 'assistants-get_alerts')
        self.assertIsNotNone(funf)
        self.assertEqual('<ul></ul>', funf(self.entity, self.user).for_html())

        # ---
        field_class = funf.search_field_builder
        self.assertIsNotNone(field_class)

        field = field_class(
            cell=EntityCellFunctionField(model=FakeOrganisation, func_field=funf),
            user=self.user,
        )
        self.assertIsInstance(field.widget, TextLVSWidget)

        to_python = field.to_python
        self.assertEqual(Q(), to_python(value=None))
        self.assertEqual(Q(), to_python(value=''))

        value = 'foobar'
        self.assertQEqual(
            Q(
                assistants_alerts__title__icontains=value,
                assistants_alerts__is_validated=False,
            ),
            to_python(value=value),
        )

    def test_function_field02(self):
        funf = function_field_registry.get(CremeEntity, 'assistants-get_alerts')

        # self._create_alert('Alert01', 'Description01', trigger_date='2011-10-21')
        self._create_alert('Alert01', 'Description01', trigger_date=date(2011, 10, 21))
        # self._create_alert('Alert02', 'Description02', trigger_date='2010-10-20')
        self._create_alert('Alert02', 'Description02', trigger_date=date(2010, 10, 20))

        # alert3 = self._create_alert('Alert03', 'Description03', trigger_date='2010-10-3')
        alert3 = self._create_alert('Alert03', 'Description03', trigger_date=date(2010, 10, 3))
        alert3.is_validated = True
        alert3.save()

        with self.assertNumQueries(1):
            result = funf(self.entity, self.user)

        self.assertEqual('<ul><li>Alert02</li><li>Alert01</li></ul>', result.for_html())

    def test_function_field03(self):
        "Prefetch with 'populate_entities()'."
        user = self.user
        # self._create_alert('Alert01', 'Description01', trigger_date='2011-10-21')
        self._create_alert('Alert01', 'Description01', trigger_date=date(2011, 10, 21))
        # self._create_alert('Alert02', 'Description02', trigger_date='2010-10-20')
        self._create_alert('Alert02', 'Description02', trigger_date=date(2010, 10, 20))

        entity02 = CremeEntity.objects.create(user=user)

        alert3 = self._create_alert(
            # 'Alert03', 'Description03', trigger_date='2010-10-3', entity=entity02,
            'Alert03', 'Description03', trigger_date=date(2010, 10, 3), entity=entity02,
        )
        alert3.is_validated = True
        alert3.save()

        # self._create_alert('Alert04', 'Description04', trigger_date='2010-10-3', entity=entity02)
        self._create_alert(
            'Alert04', 'Description04', trigger_date=date(2010, 10, 3), entity=entity02,
        )

        funf = function_field_registry.get(CremeEntity, 'assistants-get_alerts')

        with self.assertNumQueries(1):
            funf.populate_entities([self.entity, entity02], user)

        with self.assertNumQueries(0):
            result1 = funf(self.entity, user)
            result2 = funf(entity02, user)

        self.assertEqual('<ul><li>Alert02</li><li>Alert01</li></ul>', result1.for_html())
        self.assertEqual('<ul><li>Alert04</li></ul>',                 result2.for_html())

    def test_merge(self):
        def creator(contact01, contact02):
            self._create_alert('Alert01', 'Fight against him', date(2011, 1, 9),  contact01)
            self._create_alert('Alert02', 'Train with him',    date(2011, 1, 10), contact02)
            self.assertEqual(2, Alert.objects.count())

        def assertor(contact01):
            alerts = Alert.objects.all()
            self.assertEqual(2, len(alerts))

            for alert in alerts:
                # self.assertEqual(contact01, alert.creme_entity)
                self.assertEqual(contact01, alert.real_entity)

        self.aux_test_merge(creator, assertor)

    @override_settings(DEFAULT_TIME_ALERT_REMIND=60, SOFTWARE_LABEL='My CRM')
    def test_reminder1(self):
        user = self.user
        now_value = now()

        job = self.get_reminder_job()
        self.assertIsNone(job.user)
        self.assertIsNone(job.type.next_wakeup(job, now_value))

        reminder_ids = [*DateReminder.objects.values_list('id', flat=True)]

        create_alert = partial(
            Alert.objects.create,
            # creme_entity=self.entity, user=user, trigger_date=now_value,
            real_entity=self.entity, user=user, trigger_date=now_value,
        )
        alert1 = create_alert(title='Alert#1', trigger_date=now_value + timedelta(minutes=50))
        alert2 = create_alert(title='Alert#2', trigger_date=now_value + timedelta(minutes=70))
        create_alert(title='Alert#3', is_validated=True)

        self.assertLess(job.type.next_wakeup(job, now_value), now())

        self.execute_reminder_job(job)
        reminders = DateReminder.objects.exclude(id__in=reminder_ids)
        self.assertEqual(1, len(reminders))

        reminder = reminders[0]
        self.assertEqual(alert1, reminder.object_of_reminder)
        self.assertEqual(1,      reminder.ident)
        self.assertDatetimesAlmostEqual(now_value, reminder.date_of_remind, seconds=60)
        self.assertTrue(self.refresh(alert1).reminded)
        self.assertFalse(self.refresh(alert2).reminded)

        messages = mail.outbox
        self.assertEqual(1, len(messages))

        message = messages[0]
        self.assertEqual([user.email], message.to)

        software = 'My CRM'
        self.assertEqual(
            _('Reminder concerning a {software} alert related to {entity}').format(
                software=software, entity=self.entity,
            ),
            message.subject,
        )
        self.assertIn(alert1.title, message.body)
        self.assertIn(software,     message.body)

        # Reminders are not recreated if they already exist
        self.execute_reminder_job(job)
        self.assertFalse(DateReminder.objects.exclude(id__in=[*reminder_ids, reminder.id]))
        self.assertEqual(1, len(mail.outbox))

    def test_reminder2(self):
        "With null trigger date."
        job = self.get_reminder_job()
        reminder_ids = [*DateReminder.objects.values_list('id', flat=True)]

        Alert.objects.create(
            user=self.user,
            real_entity=self.entity,
            title='Title',
            trigger_date=None,
            trigger_offset={
                'cell': {'type': 'regular_field', 'value': 'birthday'},
                'sign': -1,
                'period': {'type': DaysPeriod.name, 'value': 1},
            },
        )

        self.execute_reminder_job(job)
        self.assertFalse(DateReminder.objects.exclude(id__in=reminder_ids))
        self.assertFalse(mail.outbox)

    @override_settings(DEFAULT_TIME_ALERT_REMIND=60)
    def test_reminder3(self):
        "Dynamic user."
        entity = self.entity
        entity.user = self.other_user
        entity.save()

        reminder_ids = [*DateReminder.objects.values_list('id', flat=True)]
        Alert.objects.create(
            # user=user
            real_entity=entity, trigger_date=now(),
        )

        self.execute_reminder_job(self.get_reminder_job())
        self.assertEqual(1, DateReminder.objects.exclude(id__in=reminder_ids).count())

        messages = mail.outbox
        self.assertEqual(1, len(messages))
        self.assertEqual([self.other_user.email], messages[0].to)

    @override_settings(DEFAULT_TIME_ALERT_REMIND=30)
    def test_next_wakeup1(self):
        now_value = now()

        create_alert = partial(
            Alert.objects.create,
            # creme_entity=self.entity, user=self.user, trigger_date=now_value,
            real_entity=self.entity, user=self.user, trigger_date=now_value,
        )
        create_alert(title='Alert#2', is_validated=True)
        create_alert(title='Alert#4', reminded=True)
        create_alert(title='Alert#6', trigger_date=now_value + timedelta(minutes=60))
        # Only this one should be used:
        create_alert(title='Alert#1', trigger_date=now_value + timedelta(minutes=50))
        create_alert(title='Alert#7', trigger_date=now_value + timedelta(minutes=70))
        create_alert(title='Alert#3', is_validated=True)
        create_alert(title='Alert#5', reminded=True)

        job = self.get_reminder_job()
        wakeup = job.type.next_wakeup(job, now_value)
        self.assertIsInstance(wakeup, datetime)
        self.assertDatetimesAlmostEqual(
            now_value + timedelta(minutes=20),
            wakeup,
        )

    def test_next_wakeup2(self):
        "trigger_date==NULL."
        Alert.objects.create(
            user=self.user,
            real_entity=self.entity,
            title='Title',
            trigger_date=None,
            trigger_offset={
                'cell': {'type': 'regular_field', 'value': 'birthday'},
                'sign': -1,
                'period': {'type': DaysPeriod.name, 'value': 1},
            },
        )

        job = self.get_reminder_job()
        self.assertIsNone(job.type.next_wakeup(job, now()))

    def test_manager_filter_by_user(self):
        "Teams."
        user = self.user
        now_value = now()

        create_user = get_user_model().objects.create
        teammate1 = create_user(
            username='luffy',
            email='luffy@sunny.org', role=self.role,
            first_name='Luffy', last_name='Monkey D.',
        )
        teammate2 = create_user(
            username='zorro',
            email='zorro@sunny.org', role=self.role,
            first_name='Zorro', last_name='Roronoa',
        )

        team1 = create_user(username='Team #1', is_team=True)
        team1.teammates = [teammate1, user]

        team2 = create_user(username='Team #2', is_team=True)
        team2.teammates = [self.other_user, teammate2]

        create_alert = partial(
            Alert.objects.create,
            # creme_entity=self.entity, user=user, trigger_date=now_value,
            real_entity=self.entity, user=user, trigger_date=now_value,
        )
        alert1 = create_alert(title='Alert#1')
        create_alert(title='Alert#2', user=team2)  # No (other team)
        alert3 = create_alert(title='Alert#3', user=team1)

        alerts = Alert.objects.filter_by_user(user=user)
        self.assertSetEqual({alert1, alert3}, {*alerts})
        self.assertEqual(2, len(alerts))

    def test_brick(self):
        user = self.user
        entity1 = self.entity

        state = BrickState.objects.get_for_brick_id(user=user, brick_id=AlertsBrick.id_)
        state.set_extra_data(key=BRICK_STATE_HIDE_VALIDATED_ALERTS, value=False)
        state.save()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        entity2 = create_orga(name='Acme')
        entity3 = create_orga(name='Deleted', is_deleted=True)

        def create_alert(title, entity, is_validated=False):
            return Alert.objects.create(
                user=user,
                title=title,
                # creme_entity=entity,
                real_entity=entity,
                trigger_date=now() + timedelta(days=5),
                is_validated=is_validated,
            )

        alert1 = create_alert('Recall',         entity1)
        alert2 = create_alert("It's important", entity1, is_validated=True)
        alert3 = create_alert('Other',          entity2)
        alert4 = create_alert('Ignored',        entity3)

        AlertsBrick.page_size = max(4, settings.BLOCK_SIZE)

        def alert_found(brick_node, alert):
            title = alert.title
            return any(n.text == title for n in brick_node.findall('.//td'))

        # Detail + do not hide ---
        BrickDetailviewLocation.objects.create_if_needed(
            brick=AlertsBrick,
            model=type(entity1),
            order=50,
            zone=BrickDetailviewLocation.RIGHT,
        )

        response1 = self.assertGET200(self.entity.get_absolute_url())
        detail_brick_node = self.get_brick_node(
            self.get_html_tree(response1.content), brick=AlertsBrick,
        )

        self.assertTrue(alert_found(detail_brick_node, alert1))
        self.assertTrue(alert_found(detail_brick_node, alert2))
        self.assertFalse(alert_found(detail_brick_node, alert3))

        # Home + do not hide ---
        BrickHomeLocation.objects.get_or_create(
            brick_id=AlertsBrick.id_, defaults={'order': 50},
        )

        response2 = self.assertGET200(reverse('creme_core__home'))
        home_brick_node = self.get_brick_node(
            self.get_html_tree(response2.content), brick=AlertsBrick,
        )

        self.assertTrue(alert_found(home_brick_node, alert1))
        self.assertTrue(alert_found(home_brick_node, alert2))
        self.assertTrue(alert_found(home_brick_node, alert3))
        self.assertFalse(alert_found(home_brick_node, alert4))
        self.assertInstanceLink(home_brick_node, entity1)
        self.assertInstanceLink(home_brick_node, entity2)

        # Detail + hide validated ---
        state.set_extra_data(key=BRICK_STATE_HIDE_VALIDATED_ALERTS, value=True)
        state.save()

        response3 = self.assertGET200(self.entity.get_absolute_url())
        detail_brick_node_hidden = self.get_brick_node(
            self.get_html_tree(response3.content), brick=AlertsBrick,
        )

        self.assertTrue(alert_found(detail_brick_node_hidden, alert1))
        self.assertFalse(alert_found(detail_brick_node_hidden, alert2))
        self.assertFalse(alert_found(detail_brick_node_hidden, alert3))

        # Home + hide validated ---
        response4 = self.assertGET200(reverse('creme_core__home'))
        home_brick_node_hidden = self.get_brick_node(
            self.get_html_tree(response4.content), brick=AlertsBrick,
        )

        self.assertTrue(alert_found(home_brick_node_hidden, alert1))
        self.assertFalse(alert_found(home_brick_node_hidden, alert2))
        self.assertTrue(alert_found(home_brick_node_hidden, alert3))
        self.assertFalse(alert_found(home_brick_node_hidden, alert4))

    def test_brick_hide_validated_alerts(self):
        user = self.user

        def get_state():
            return BrickState.objects.get_for_brick_id(user=user, brick_id=AlertsBrick.id_)

        self.assertIsNone(get_state().pk)

        url = reverse('assistants__hide_validated_alerts')
        self.assertGET405(url)

        # ---
        self.assertPOST200(url, data={'value': 'true'})
        state1 = get_state()
        self.assertIsNotNone(state1.pk)
        self.assertIs(
            state1.get_extra_data(BRICK_STATE_HIDE_VALIDATED_ALERTS),
            True,
        )

        # ---
        self.assertPOST200(url, data={'value': '0'})
        self.assertIs(
            get_state().get_extra_data(BRICK_STATE_HIDE_VALIDATED_ALERTS),
            False,
        )
