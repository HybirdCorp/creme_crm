# -*- coding: utf-8 -*-

# The following code is an heavy modification of:
#  https://djangosnippets.org/snippets/3003/

################################################################################
# Copyright (c)  2013  asfaltboy
# Copyright (c)  2015-2021  Hybird
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
from datetime import date, datetime

from django.core.serializers.base import SerializationError
from django.db.models import Model, Q
from django.db.models.query import QuerySet

from . import dates

logger = logging.getLogger(__name__)


class QSerializer:
    """A Q object serializer base class.

    By default, the class provides loads/dumps methods which wrap around
    JSON serialization, but they may be easily overwritten to serialize
    into other formats (i.e XML, YAML, etc...).
    """
    def _serialize_value(self, value):
        if isinstance(value, date):
            # TODO: same format for deserialization...
            # return value.strftime(
            #     DATETIME_ISO8601_FMT
            #     if isinstance(value, datetime) else
            #     DATE_ISO8601_FMT
            # )
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

    def deserialize(self, d: dict) -> Q:
        query = Q()
        query.children = [
            self.deserialize(child) if isinstance(child, dict) else child
            for child in d['val']
        ]

        op = d['op']
        query.connector, query.negated = (op[:1], True) if op.startswith('N') else (op, False)

        return query

    def dumps(self, obj: Q) -> str:
        try:
            return json.dumps(self.serialize(obj), separators=(',', ':'))
        except Exception:
            logger.exception('QSerializer.dumps(): error when serializing <%s>', obj)
            raise

    def loads(self, string: str) -> Q:
        try:
            return self.deserialize(json.loads(string))
        except Exception:
            logger.exception('QSerializer.loads(): error when deserializing <%s>', string)
            raise
