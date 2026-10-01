# The following code is a heavy modification of:
#  https://djangosnippets.org/snippets/3003/

################################################################################
# Copyright (c)  2013  asfaltboy
# Copyright (c)  2015-2026  Hybird
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
#     1. Redistributions of source code must retain the above copyright notice,
#        this list of conditions and the following disclaimer.
#
#     2. Redistributions in binary form must reproduce the above copyright
#        notice, this list of conditions and the following disclaimer in the
#        documentation and/or other materials provided with the distribution.
#
#     3. Neither the name of Django nor the names of its contributors may be used
#        to endorse or promote products derived from this software without
#        specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
# ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
################################################################################

import json
import logging
import warnings
from collections.abc import Callable, Sequence
from datetime import date, datetime
from typing import Any

from django.core.exceptions import (
    FieldDoesNotExist,
    FieldError,
    PermissionDenied,
)
from django.core.serializers.base import SerializationError
from django.db.models import Model, Q, QuerySet
from django.db.models.sql import Query

from . import dates

logger = logging.getLogger(__name__)
_NOT_SET = object()


class QSerializer:
    """A Q object serializer base class.

    By default, the class provides loads/dumps methods which wrap around
    JSON serialization, but they may be easily overwritten to serialize
    into other formats (i.e. XML, YAML, etc…).
    """
    class PathError(Exception):
        pass

    def _serialize_value(self, value):
        if isinstance(value, date):
            # TODO: same format for deserialization…
            if isinstance(value, datetime):
                return dates.to_utc(value).strftime(dates.DATETIME_ISO8601_FMT)
            else:
                return value.strftime(dates.DATE_ISO8601_FMT)

        if isinstance(value, Model):
            return value.pk

        return value

    def serialize(self, q: Q) -> dict:
        children: list = []

        for child in q.children:
            if isinstance(child, Q):
                children.append(self.serialize(child))
            else:
                key, value = child

                if isinstance(value, QuerySet):
                    raise SerializationError('QSerializer: QuerySets are not managed')

                if key.endswith('__range') or key.endswith('__in'):
                    value = [self._serialize_value(part) for part in value]
                else:
                    value = self._serialize_value(value)

                children.append((key, value))

        return {
            'op': 'N' + q.connector if q.negated else q.connector,
            'val': children,
        }

    def _check_path_n_value(self, model, path, value, field_checkers=()):
        # NB: Query.build_filter() returns notably a WhereNode which is too low level
        #      to perform simple check
        try:
            Query(model=model).build_filter(Q(**{path: value}))
        except FieldError as e:
            raise self.PathError(f'Invalid field "{model.__name__}.{path}"') from e

        depth = 0
        current_model = model
        for field_name in path.split('__'):
            try:
                field = current_model._meta.get_field(field_name)
            except FieldDoesNotExist:
                break
            else:
                try:
                    for checker in field_checkers:
                        checker(field=field, depth=depth)
                except PermissionDenied as e:
                    raise self.PathError(str(e)) from e

                remote_field = getattr(field, 'remote_field', None)
                if remote_field is None:
                    break

                depth += 1
                current_model = remote_field.model

    def _check_child(self, child: tuple[str, Any], model, field_checkers=()) -> tuple[str]:
        if len(child) != 2:
            raise self.PathError('"val" must be a list of couples')

        if model is _NOT_SET:  # DEPRECATED
            return child

        if not isinstance(child[0], str):
            raise self.PathError('First value of couples must be a string')

        self._check_path_n_value(
            model=model, path=child[0], value=child[1], field_checkers=field_checkers,
        )

        return child

    # def deserialize(self, d: dict) -> Q:
    def deserialize(self, d: dict, *, model=_NOT_SET, field_checkers=()) -> Q:
        """Build a Q instance from a dictionary.
        @param d: Serialized Q which can be built by the method 'serialize()'.
        @param model: see 'loads()'.
        @param field_checkers: see 'loads()'.
        @return The deserialized 'Q'.
        """
        if model is _NOT_SET:
            warnings.warn(
                'QSerializer.deserialize() should receive an argument "model"',
                DeprecationWarning,
            )

            if field_checkers:
                logger.critical(
                    'QSerializer.deserialize() does not use "field_checkers" '
                    'if model is not given.'
                )

        query = Q()
        query.children = [
            self.deserialize(child)
            if isinstance(child, dict) else
            # NB: we re-build a tuple because deserialization gives us lists;
            #     it works, but it's not the natural type we get when instancing a Q
            #     & so it makes unit testing more difficult.
            self._check_child(tuple(child), model=model, field_checkers=field_checkers)
            for child in d['val']
        ]

        op = d['op']
        query.connector, query.negated = (op[:1], True) if op.startswith('N') else (op, False)

        return query

    def dumps(self, obj: Q) -> str:
        """Serialize a Q instance as a JSON string.
        This string can then be deserialized by the method 'loads()'.
        """
        try:
            return json.dumps(self.serialize(obj), separators=(',', ':'))
        except Exception:
            logger.exception('QSerializer.dumps(): error when serializing <%s>', obj)
            raise

    def loads(self, string: str, *,
              model=_NOT_SET,
              field_checkers: Sequence[Callable] = (),
              ) -> Q:
        """Load a JSON string and build a Q instance.
        @param string: data to load. Can be generated by the method 'dumps()'.
        @param model: Model class related to the query; it's used to make some checks.
               Not giving it is deprecated (no check-mode).
        @param field_checkers Each checkers is a function which take the arguments
               "field" (Field instance)  & "depth" (integer) & can raise a
               'PermissionDenied' exception if an error is detected.
        @return The deserialized 'Q'.
        """
        if model is _NOT_SET:
            warnings.warn(
                'QSerializer.loads() should receive an argument "model"',
                DeprecationWarning,
            )

        try:
            d = json.loads(string)
            if not isinstance(d, dict):
                raise ValueError('Data must be a dict')

            # return self.deserialize(d)
            return self.deserialize(d, model=model, field_checkers=field_checkers)
        except Exception:
            logger.exception('QSerializer.loads(): error when deserializing <%s>', string)
            raise
