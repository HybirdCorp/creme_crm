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

# TODO: rename to use in other place than CustomFields??

from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal, DecimalException

from django.utils.timezone import now

from creme.creme_core.utils import dates as dates_utils

logger = logging.getLogger(__name__)


# TODO: typing
# TODO: doc
class DefaultValueMaker:
    type_id = ''  # Override in child classes

    @classmethod
    def from_dict(cls, /, data: dict) -> DefaultValueMaker:
        raise NotImplementedError

    def make(self):
        raise NotImplementedError

    def to_dict(self):
        return {'type': self.type_id}


class NoneMaker(DefaultValueMaker):
    @classmethod
    def from_dict(cls, /, data):
        return cls()

    def make(self):
        return None

    # TODO?
    # def to_dict(self):
    #     return {}


class IntegerMaker(DefaultValueMaker):
    type_id = 'int'
    _value: int

    def __init__(self, value):
        self._value = int(value)

    @classmethod
    def from_dict(cls, /, data):
        # value = data['value']
        # if not isinstance(value, int):
        #     raise ValueError(
        #         f'{cls.__name__}: value should be an integer (got {type(value)})'
        #     )
        #
        # maker = cls()
        # maker._value = value
        #
        # return maker
        return cls(data['value'])

    def make(self):
        return self._value

    def to_dict(self):
        d = super().to_dict()
        d['value'] = self._value

        return d


# TODO: factorise? (SimpleValueMaker??)
class BooleanMaker(DefaultValueMaker):
    type_id = 'bool'
    _value: bool

    def __init__(self, value):
        self._value = bool(value)

    @classmethod
    def from_dict(cls, /, data):
        # value = data['value']
        # if not isinstance(value, bool):
        #     raise ValueError(
        #         f'{cls.__name__}: value should be an boolean (got {type(value)})'
        #     )
        #
        # maker = cls()
        # maker._value = value
        #
        # return maker
        return cls(data['value'])

    def make(self):
        return self._value

    def to_dict(self):
        d = super().to_dict()
        d['value'] = self._value

        return d


class DecimalMaker(DefaultValueMaker):
    type_id = 'decimal'
    _value: Decimal

    def __init__(self, value):
        try:
            self._value = Decimal(value)
        except DecimalException as e:
            raise ValueError(f'{type(self).__name__}: value should be an decimal string') from e

    @classmethod
    def from_dict(cls, /, data):
        # try:
        #     value = Decimal(data['value'])
        # except DecimalException as e:
        #     raise ValueError(f'{cls.__name__}: value should be an decimal string') from e
        #
        # maker = cls()
        # maker._value = value
        #
        # return maker
        return cls(data['value'])

    def make(self):
        return self._value

    def to_dict(self):
        d = super().to_dict()
        d['value'] = str(self._value)

        return d


class StringMaker(DefaultValueMaker):
    type_id = 'str'
    _value: str

    def __init__(self, value):
        self._value = str(value)

    @classmethod
    def from_dict(cls, /, data):
        # value = data['value']
        # if not isinstance(value, str):
        #     raise ValueError(
        #         f'{cls.__name__}: value should be a string (got {type(value)})'
        #     )
        #
        # maker = cls()
        # maker._value = value
        #
        # return maker
        return cls(data['value'])

    def make(self):
        return self._value

    def to_dict(self):
        d = super().to_dict()
        d['value'] = str(self._value)

        return d


class DateMaker(DefaultValueMaker):
    type_id = 'date'
    _value: date | None

    @classmethod
    def from_dict(cls, /, data):
        str_date = data.get('value')
        if str_date is None:
            try:
                op = data['op']
            except KeyError as e:
                raise ValueError(f'{cls.__name__}: available keys are: value, op') from e

            if op != 'today':
                raise ValueError(f'{cls.__name__}: available operator is "today"')

            value = None
        else:
            if not isinstance(str_date, str):
                raise ValueError(f'{cls.__name__}: value should be a ISO8601 date')

            try:
                value = dates_utils.date_from_ISO8601(str_date)
            except ValueError as e:
                raise ValueError(f'{cls.__name__}: {e}') from e

        maker = cls()
        maker._value = value

        return maker

    def make(self):
        value = self._value
        return date.today() if value is None else value

    def to_dict(self):
        d = super().to_dict()
        value = self._value
        if value is None:
            d['op'] = 'today'
        else:
            d['value'] = dates_utils.date_to_ISO8601(value)

        return d


# TODO: factorise
class DatetimeMaker(DefaultValueMaker):
    type_id = 'datetime'
    _value: datetime | None

    @classmethod
    def from_dict(cls, /, data):
        str_dt = data.get('value')
        if str_dt is None:
            try:
                op = data['op']
            except KeyError as e:
                raise ValueError(f'{cls.__name__}: available keys are: value, op') from e

            if op != 'now':
                raise ValueError(f'{cls.__name__}: available operator is "now"')

            value = None
        else:
            if not isinstance(str_dt, str):
                raise ValueError(f'{cls.__name__}: value should be a ISO8601 datetime')

            try:
                value = dates_utils.dt_from_ISO8601(str_dt)
            except ValueError as e:
                raise ValueError(f'{cls.__name__}: {e}') from e

        maker = cls()
        maker._value = value

        return maker

    def make(self):
        value = self._value
        return now() if value is None else value

    def to_dict(self):
        d = super().to_dict()
        value = self._value
        if value is None:
            d['op'] = 'now'
        else:
            d['value'] = dates_utils.dt_to_ISO8601(value)

        return d


class DefaultValueMakerRegistry:
    def __init__(self):
        self._maker_classes = {}

    def get_maker(self, /, data: dict) -> DefaultValueMaker:
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

    def register(self, *maker_classes: type[DefaultValueMaker]) -> DefaultValueMakerRegistry:
        classes = self._maker_classes

        for cls in maker_classes:
            classes[cls.type_id] = cls

        return self


value_maker_registry = DefaultValueMakerRegistry().register(
    IntegerMaker, BooleanMaker, DecimalMaker,
    StringMaker,
    DateMaker, DatetimeMaker,
)
