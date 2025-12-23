################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2025  Hybird
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

from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal, DecimalException

from django.utils.formats import date_format, number_format
from django.utils.timezone import localtime, now
from django.utils.translation import gettext as _

from creme.creme_core.utils import dates as dates_utils

logger = logging.getLogger(__name__)


class ValueMaker:
    """A maker can produce value --fixed or dynamic-- of a specific type with
    their main method: make().
    They can be serialized (classically to JSON) which their method 'to_dict()';
    the serialized data contain a "type" key which can be used by a
    'ValueMakerRegistry' instance to de-serialize them correctly.

    Makers are currently used by CustomFields to store their default value.
    But why just not simply store an integer in a JSONField to store the default
    value of an INT CustomField? Because there are more complex cases, like
    date & datetime.
     - The deserialization phase must produce instances of 'datetime.date' &
       'datetime.datetime', not just strings representing formatted dates.
     - We want to propose dynamic values 'today'/'now', & so we have to encode
       this cases.
    Note than dynamic values could potentially be interesting even for other
    types (e.g. "current temperature" for INT), dates are just the current
    obvious use-case.
    """
    # This string is used to identify each child class, and so must be overridden in them
    type_id = ''

    @classmethod
    def from_dict(cls, /, data: dict) -> ValueMaker:
        "Builds an instance from a dictionary (produced by the method 'to_dict()')."
        raise NotImplementedError

    def make(self):
        raise NotImplementedError

    def render(self) -> str:
        "Returns a human-friendly string which can be use by the configuration UI."
        return ''

    def to_dict(self) -> dict:
        "Returns a JSON-friendly dictionary use to serialize the instance."
        # The key "type" is used by the registry to build an instance of the
        # correct class. Child classes MUST KEEP this key.
        return {'type': self.type_id}


class NoneMaker(ValueMaker):
    @classmethod
    def from_dict(cls, /, data):
        return cls()

    def make(self):
        return None

    # TODO?
    # def to_dict(self):
    #     return {}


class IntegerMaker(ValueMaker):
    type_id = 'int'
    _value: int

    def __init__(self, value: int | str):
        self._value = int(value)

    def __eq__(self, other):
        return isinstance(other, type(self)) and self._value == other._value

    @classmethod
    def from_dict(cls, /, data):
        return cls(data['value'])

    def make(self):
        return self._value

    def render(self):
        return number_format(self._value, force_grouping=True)

    def to_dict(self):
        d = super().to_dict()
        d['value'] = self._value

        return d


# TODO: factorise? (SimpleValueMaker?)
class BooleanMaker(ValueMaker):
    type_id = 'bool'
    _value: bool

    def __init__(self, value):
        self._value = bool(value)

    def __eq__(self, other):
        return isinstance(other, type(self)) and self._value == other._value

    @classmethod
    def from_dict(cls, /, data):
        return cls(data['value'])

    def make(self):
        return self._value

    def render(self):
        return _('Yes') if self._value else _('No')

    def to_dict(self):
        d = super().to_dict()
        d['value'] = self._value

        return d


class DecimalMaker(ValueMaker):
    type_id = 'decimal'
    _value: Decimal

    def __init__(self, value: str | Decimal):
        try:
            self._value = Decimal(value)
        except DecimalException as e:
            raise ValueError(
                f'{type(self).__name__}: value should be an decimal string'
            ) from e

    def __eq__(self, other):
        return isinstance(other, type(self)) and self._value == other._value

    @classmethod
    def from_dict(cls, /, data):
        return cls(data['value'])

    def make(self):
        return self._value

    def render(self):
        return number_format(self._value, force_grouping=True)

    def to_dict(self):
        d = super().to_dict()
        d['value'] = str(self._value)

        return d


class StringMaker(ValueMaker):
    type_id = 'str'
    _str: str

    def __init__(self, value):
        self._str = str(value)

    def __eq__(self, other):
        return isinstance(other, type(self)) and self._str == other._str

    @classmethod
    def from_dict(cls, /, data):
        return cls(data['value'])

    def make(self):
        return self._str

    def render(self):
        return self._str

    def to_dict(self):
        d = super().to_dict()
        d['value'] = str(self._str)

        return d


class DateMaker(ValueMaker):
    """This maker propose to store:
     - A fixed date
     - An operator "today"; the method make() will produce a dynamic value.
    """
    type_id = 'date'
    _date: date | None

    def __eq__(self, other):
        return isinstance(other, type(self)) and self._date == other._date

    @classmethod
    def from_date(cls, /, date_obj: date):
        maker = cls()
        maker._date = date_obj

        return maker

    @classmethod
    def from_operator(cls, /, op: str):
        if op != 'today':
            raise ValueError(f'{cls.__name__}: available operator is "today"')

        maker = cls()
        maker._date = None

        return maker

    @classmethod
    def from_dict(cls, /, data):
        str_date = data.get('value')
        if str_date is None:
            try:
                op = data['op']
            except KeyError as e:
                raise ValueError(f'{cls.__name__}: available keys are: value, op') from e

            return cls.from_operator(op)

        if not isinstance(str_date, str):
            raise ValueError(f'{cls.__name__}: value should be a ISO8601 date')

        try:
            date_obj = dates_utils.date_from_ISO8601(str_date)
        except ValueError as e:
            raise ValueError(f'{cls.__name__}: {e}') from e

        return cls.from_date(date_obj)

    def make(self):
        value = self._date
        return date.today() if value is None else value

    def render(self):
        return date_format(self._date, 'DATE_FORMAT')

    def to_dict(self):
        d = super().to_dict()
        date_obj = self._date
        if date_obj is None:
            d['op'] = 'today'
        else:
            d['value'] = dates_utils.date_to_ISO8601(date_obj)

        return d


# TODO: factorise
class DateTimeMaker(ValueMaker):
    """This maker propose to store:
     - A fixed datetime
     - An operator "now"; the method make() will produce a dynamic value.
    """
    type_id = 'datetime'
    _dt: datetime | None

    def __eq__(self, other):
        return isinstance(other, type(self)) and self._dt == other._dt

    @classmethod
    def from_datetime(cls, /, dt):
        maker = cls()
        maker._dt = dt

        return maker

    @classmethod
    def from_operator(cls, /, op: str):
        if op != 'now':
            raise ValueError(f'{cls.__name__}: available operator is "now"')

        maker = cls()
        maker._dt = None

        return maker

    @classmethod
    def from_dict(cls, /, data):
        str_dt = data.get('value')
        if str_dt is None:
            try:
                op = data['op']
            except KeyError as e:
                raise ValueError(f'{cls.__name__}: available keys are: value, op') from e

            return cls.from_operator(op)

        if not isinstance(str_dt, str):
            raise ValueError(f'{cls.__name__}: value should be a ISO8601 datetime')

        try:
            dt = dates_utils.dt_from_ISO8601(str_dt)
        except ValueError as e:
            raise ValueError(f'{cls.__name__}: {e}') from e

        return cls.from_datetime(dt)

    def make(self):
        dt = self._dt
        return now() if dt is None else dt

    def render(self):
        return date_format(localtime(self._dt), 'DATETIME_FORMAT')

    def to_dict(self):
        d = super().to_dict()
        dt = self._dt
        if dt is None:
            d['op'] = 'now'
        else:
            d['value'] = dates_utils.dt_to_ISO8601(dt)

        return d


class ValueMakerRegistry:
    """This registry is used to deserialize instances of ValueMaker."""
    # The keys are ValueMaker.type_id
    _maker_classes: dict[str, type[ValueMaker]]

    def __init__(self):
        self._maker_classes = {}

    def get_maker(self, /, data: dict) -> ValueMaker:
        """The "data" parameter is a dictionary produced by <ValueMaker.to_dict()>"""
        type_id = data.get('type')
        if not type_id:
            return NoneMaker()

        cls = self._maker_classes.get(type_id)
        if not cls:
            logger.warning(
                f'{type(self).__name__}: maker class with type_id="{type_id}" not found'
            )

            return NoneMaker()

        return cls.from_dict(data)

    def register(self, *maker_classes: type[ValueMaker]) -> ValueMakerRegistry:
        """Register the classes which the registry is able to deserialize."""
        classes = self._maker_classes

        for cls in maker_classes:
            classes[cls.type_id] = cls

        return self


value_maker_registry = ValueMakerRegistry().register(
    IntegerMaker, BooleanMaker, DecimalMaker,
    StringMaker,
    DateMaker, DateTimeMaker,
)
