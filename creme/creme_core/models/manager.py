# Code derived from http://stackoverflow.com/questions/15121093/django-adding-nulls-last-to-query

################################################################################
#
# Copyright (c) 2013 Tim Babych
# Copyright (c) 2016 Daniel Hahler
# Copyright (c) 2016-2025 Hybird
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
################################################################################

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import connections, models
from django.db.models.sql.compiler import SQLCompiler

if TYPE_CHECKING:
    from .entity import CremeEntity


class LowNullsSQLCompiler(SQLCompiler):
    """SQL compiler which orders NULL values as low values.
    So it injects 'NULLS FIRST/LAST' into queries (on PostgreSQL only).
    """
    def get_order_by(self):
        result = super().get_order_by()

        if result and self.connection.vendor == 'postgresql':
            # NB: PostgreSQL accepts NULLS LAST/FIRST even on columns which
            #     cannot be NULL, so we do not check it.
            return [
                (
                    expr,
                    (sql + (' NULLS LAST' if expr.descending else ' NULLS FIRST'), params, is_ref)
                ) for (expr, (sql, params, is_ref)) in result
            ]

        return result


class LowNullsQuery(models.sql.query.Query):
    """Uses a LowNullsSQLCompiler"""
    def get_compiler(self, using=None, connection=None, elide_empty=True):
        if using is None:
            if connection is None:
                raise ValueError('Need either using or connection')
        else:
            connection = connections[using]

        return LowNullsSQLCompiler(
            self, connection=connection, using=using, elide_empty=elide_empty,
        )


class LowNullsQuerySet(models.QuerySet):
    def __init__(self, model=None, query=None, using=None, hints=None):
        super().__init__(model, query, using, hints)
        self.query = query or LowNullsQuery(self.model)


class CremeEntityManager(models.Manager.from_queryset(LowNullsQuerySet)):
    def get_by_portable_key(self, key) -> CremeEntity:
        """See CremeEntity.portable_key()."""
        return self.get(uuid=key)
