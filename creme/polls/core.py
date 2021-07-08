# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2012-2021  Hybird
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
################################################################################

from collections import OrderedDict
from datetime import date
from json import loads as json_load

from django.core.exceptions import ValidationError
from django.forms.fields import (
    CharField,
    DateField,
    Field,
    IntegerField,
    MultipleChoiceField,
    TypedChoiceField,
)
from django.forms.widgets import RadioSelect, Textarea
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme.creme_core.forms.fields import ChoiceOrCharField
from creme.creme_core.forms.widgets import UnorderedMultipleChoiceWidget
from creme.creme_core.utils.dates import date_2_dict
from creme.creme_core.utils.serializers import json_encode


class PollLineType:
    verbose_name = '??'
    editable = True

    INT            = 1
    # DECIMAL        = 2
    BOOL           = 3
    STRING         = 10
    TEXT           = 11
    DATE           = 20
    # TIME           = 21
    # DATE_TIME      = 22
    # YEAR           = 23
    # MONTH          = 24
    # DAY            = 25
    HOUR           = 26
    ENUM           = 100
    MULTI_ENUM     = 101
    ENUM_OR_STRING = 102
    COMMENT        = 255

    def __init__(self, **kwargs):
        self._args = {}

    @staticmethod
    def build_from_serialized_args(ptype, raw_args):
        kwargs = json_load(raw_args) if raw_args else {}

        return POLL_LINE_TYPES[ptype](**kwargs)

    @staticmethod
    def build_serialized_args(ptype, **kwargs):
        return POLL_LINE_TYPES[ptype](**kwargs).serialized_args()

    def _cast_answer_4_decoding(self, answer):
        return answer

    def _cast_answer_4_encoding(self, answer):
        return answer

    @staticmethod
    def choices():
        return [
            (i, pltype.verbose_name)
            for i, pltype in POLL_LINE_TYPES.items()
        ]

    def _cleaned_args(self):
        return self._args

    def cleaned_serialized_args(self):
        "Return a cleaned copy of the args (to be used in Replies)."
        args = self._cleaned_args()
        return json_encode(args) if args else None

    def decode_answer(self, raw_answer):
        return (
            self._cast_answer_4_decoding(json_load(raw_answer))
            if raw_answer is not None else
            None
        )

    def decode_condition(self, raw_cond_answer):
        return self._cast_answer_4_decoding(json_load(raw_cond_answer))

    @property
    def description(self):
        return self.verbose_name

    def encode_answer(self, raw_answer):
        return (
            json_encode(self._cast_answer_4_encoding(raw_answer))
            if raw_answer is not None else
            None
        )

    def encode_condition(self, cond_answer):
        """@param cond_answer Value of answer in condition."""
        return json_encode(cond_answer)

    def _formfield(self, initial):
        if not self.editable:
            raise Exception('This type is not editable.')

        return Field()

    def formfield(self, initial_raw_answer):
        return self._formfield(
            None
            if initial_raw_answer is None else
            json_load(initial_raw_answer)
        )

    def get_choices(self):
        """Get the choices that are proposed to the user for this question type.
        @return A sequence of (id, label) if this type has choices, else None.
        """
        return None

    def get_editable_choices(self):
        "Like get_choices(), but only editable choices are returned."
        return None

    def is_condition_met(self, raw_answer, raw_cond_answer):
        return self.decode_answer(raw_answer) == self.decode_condition(raw_cond_answer)

    def serialized_args(self):
        args = self._args
        # return json_dump(args) if args else None
        return json_encode(args) if args else None

    def get_stats(self, raw_answer):
        answer = self.decode_answer(raw_answer)
        return [(answer, 1)] if answer is not None else []

    def _get_choices_stats(self, answer, choices):
        if isinstance(answer, list):
            return [
                (choice[1], 1 if choice[1] in answer else 0)
                for choice in choices
            ]

        return [
            (choice[1], 1 if choice[1] == answer else 0)
            for choice in choices
        ]


class IntPollLineType(PollLineType):
    verbose_name = _('Integer')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        args = self._args

        def extract(arg):  # TODO: move to creme_core.utils ??
            bound = kwargs.get(arg)
            if bound is not None:
                args[arg] = bound  # TODO validate that it is an int ? (done in the form for now)

            return bound

        lower_bound = extract('lower_bound')
        upper_bound = extract('upper_bound')

        if lower_bound is not None and upper_bound is not None:
            if lower_bound >= upper_bound:
                raise ValidationError(
                    gettext('The upper bound must be greater than the lower bound.'),
                    code='invalid_bounds',
                )

    @property
    def description(self):
        get_arg = self._args.get
        min_value = get_arg('lower_bound')
        max_value = get_arg('upper_bound')

        if min_value is None:
            if max_value is None:
                return self.verbose_name

            return gettext('Integer less than {max_value}').format(max_value=max_value)

        if max_value is None:
            return gettext('Integer greater than {min_value}').format(min_value=min_value)

        return gettext('Integer between {min_value} and {max_value}').format(
            min_value=min_value,
            max_value=max_value,
        )

    def _formfield(self, initial):
        get_arg = self._args.get
        return IntegerField(
            min_value=get_arg('lower_bound'),
            max_value=get_arg('upper_bound'),
            initial=initial,
        )


class BoolPollLineType(PollLineType):
    verbose_name = _('Boolean (Yes/No)')
    _CHOICES = OrderedDict([
        (0, _('No')),
        (1, _('Yes')),
    ])

    def _cast_answer_4_decoding(self, answer):
        return self._CHOICES[answer]

    def _formfield(self, initial):
        return TypedChoiceField(
            choices=self._CHOICES.items(),
            coerce=int,
            widget=RadioSelect,
            initial=initial,
            empty_value=None,
        )

    def get_choices(self):
        return [(k, str(v)) for k, v in self._CHOICES.items()]

    def get_stats(self, raw_answer):
        answer = self.decode_answer(raw_answer)
        return self._get_choices_stats(
            answer, self.get_choices(),
        ) if answer is not None else []


class StringPollLineType(PollLineType):
    verbose_name = _('String')

    def _formfield(self, initial):
        return CharField(initial=initial)

    def get_stats(self, raw_answer):
        return None


class TextPollLineType(PollLineType):
    verbose_name = _('Text area')

    def _formfield(self, initial):
        return CharField(widget=Textarea(), initial=initial)

    def get_stats(self, raw_answer):
        return None


class DatePollLineType(PollLineType):
    verbose_name = _('Date')

    def _cast_answer_4_encoding(self, answer):
        return date_2_dict(answer)

    def _cast_answer_4_decoding(self, answer):
        return date(**answer)

    def _formfield(self, initial):
        return DateField(
            initial=None if initial is None else date(**initial),
        )

    def get_stats(self, raw_answer):
        return None


class HourPollLineType(PollLineType):
    verbose_name = _('Hour')

    def formfield(self, initial):
        return IntegerField(min_value=0, max_value=23, initial=initial)


class EnumPollLineType(PollLineType):
    verbose_name = _('Choice list')
    _description = _('Choice list ({})')
    _description_del = _('Choice list ({choices}) (deleted: {del_choices})')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        choices = kwargs.get('choices') or ()

        if len(choices) < 2:
            raise ValidationError(gettext('Give 2 choices at least.'))

        self._args['choices'] = choices

        del_choices = kwargs.get('del_choices')
        if del_choices:
            self._args['del_choices'] = del_choices

    def _cast_answer_4_decoding(self, answer):
        for k, v in self._args['choices']:  # TODO: build a dict a keep in cache ?
            if answer == k:
                return v

    def _cleaned_args(self):
        return {'choices': self._args['choices']}  # del_choices are not copied

    @property
    def description(self):
        join = self._joined_choices
        choices = join(self._args['choices'])
        del_choices = self.get_deleted_choices()

        if del_choices:
            return self._description_del.format(
                choices=choices, del_choices=join(del_choices),
            )

        return self._description.format(choices)

    def _formfield(self, initial):
        return TypedChoiceField(
            choices=self._args['choices'],
            coerce=int,
            initial=initial,
            empty_value=None,
        )

    def get_choices(self):
        return self._args['choices']  # TODO: copy ??

    def get_deleted_choices(self):  # TODO: in base interface ???
        return self._args.get('del_choices') or ()

    def get_editable_choices(self):
        return self.get_choices()

    def _joined_choices(self, choices):
        return ' / '.join(item[1] for item in choices)

    def get_stats(self, raw_answer):
        answer = self.decode_answer(raw_answer)
        return self._get_choices_stats(
            answer, self.get_choices(),
        ) if answer is not None else []


class MultiEnumPollLineType(EnumPollLineType):
    verbose_name = _('Multiple choice list')
    _description = _('Multiple choice list ({})')
    _description_del = _(
        'Multiple choice list ({choices}) (deleted: {del_choices})'
    )

    def _cast_answer_4_decoding(self, answer):
        indices = {*answer}

        return [v for k, v in self._args['choices'] if k in indices]

    def _cast_answer_4_encoding(self, answer):
        return [int(i) for i in answer]

    def encode_condition(self, cond_answer):
        # TODO: cond_answer as list of choice (later with better operators)
        return json_encode([cond_answer])

    def _formfield(self, initial):
        return MultipleChoiceField(
            choices=self._args['choices'],
            initial=initial,
            widget=UnorderedMultipleChoiceWidget(columntype='wide'),
        )

    def is_condition_met(self, raw_answer, raw_cond_answer):
        answer = self.decode_answer(raw_answer) or ()

        return any(e in answer for e in self.decode_condition(raw_cond_answer))


class EnumOrStringPollLineType(EnumPollLineType):
    verbose_name = _('Choice list with free choice')
    _description = _('Choice list with free choice ({})')
    _description_del = _(
        'Choice list with free choice ({choices}) (deleted: {del_choices})'
    )

    def _cast_answer_4_decoding(self, answer):
        if len(answer) == 1:
            return super()._cast_answer_4_decoding(answer[0])

        return answer[1]

    def _cast_answer_4_encoding(self, answer):
        index = answer[0]
        return answer if not index else [index]

    def decode_condition(self, raw_cond_answer):  # TODO; factorise better like decode_answer() ??
        choice = json_load(raw_cond_answer)[0]  # [TODO: if len(cond_answer) > 1]

        return super()._cast_answer_4_decoding(choice) if choice else gettext('Other')

    def encode_condition(self, cond_answer):
        # NB: we use a (json) list, in order to encode complexier conditions later,
        #     eg: [0, 'My user string']
        return json_encode([cond_answer])

    def _formfield(self, initial):
        return ChoiceOrCharField(choices=self._args['choices'], initial=initial)

    def get_choices(self):
        return [
            (0, gettext('Other')),
            *self._args['choices'],
        ]

    def get_editable_choices(self):
        return self._args['choices']

    def is_condition_met(self, raw_answer, raw_cond_answer):
        return (
            False
            if raw_answer is None else
            json_load(raw_answer)[0] == json_load(raw_cond_answer)[0]
        )

    def get_stats(self, raw_answer):
        answer = self.decode_answer(raw_answer)
        stats = []

        if answer is not None:
            in_choices = False
            stats_append = stats.append

            for choice in self.get_choices()[1:]:
                label = choice[1]
                count = 1 if answer == label else 0
                in_choices |= count

                stats_append((label, count))

            stats_append((gettext('Other'), 0 if in_choices else 1))

        return stats


class CommentPollLineType(PollLineType):
    verbose_name = _('Comment')
    editable = False

    def get_stats(self, raw_answer):
        return None


POLL_LINE_TYPES = OrderedDict([
    (PollLineType.INT,            IntPollLineType),
    (PollLineType.BOOL,           BoolPollLineType),
    (PollLineType.STRING,         StringPollLineType),
    (PollLineType.TEXT,           TextPollLineType),
    (PollLineType.DATE,           DatePollLineType),
    (PollLineType.HOUR,           HourPollLineType),
    (PollLineType.ENUM,           EnumPollLineType),
    (PollLineType.MULTI_ENUM,     MultiEnumPollLineType),
    (PollLineType.ENUM_OR_STRING, EnumOrStringPollLineType),
    (PollLineType.COMMENT,        CommentPollLineType),
])
