# -*- coding: utf-8 -*-

# Small modification of http://djangosnippets.org/snippets/1672/
# Author: davepeck
# License: Public Domain

from django.db import connection
from django.template import Template, Context
from django.conf import settings


_TEMPLATE = Template("""
QUERIES: {{count}} quer{{count|pluralize:"y,ies"}} in {{time}} seconds:
{% for sql in sqllog %}
  [{{forloop.counter}}] {{sql.time}}s: {{sql.sql|safe}}
{% endfor %}""")


class SQLLogToConsoleMiddleware(object):
    """ Log all SQL statements direct to the console.
    Intended for use with the django development server.
    """

    def process_response(self, request, response):
        queries = connection.queries

        #if queries:
        if queries and len(queries) > 1: #filter queries with only session retrieving
            print _TEMPLATE.render(Context({
                    'sqllog': queries,
                    'count':  len(queries),
                    'time':   sum(float(q['time']) for q in queries)
                }))

        return response
