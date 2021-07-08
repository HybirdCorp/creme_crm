# -*- coding: utf-8 -*-

from datetime import datetime

from django.template import Context, Template
from django.utils.translation import ngettext

from ..base import CremeTestCase


class CremeDateTagsTestCase(CremeTestCase):
    def test_date_timedelta_pprint(self):
        with self.assertNoException():
            template = Template(
                r'{% load creme_date %}'
                '{{d1|date_timedelta_pprint}}#'
                '{{d2|date_timedelta_pprint}}#'
                '{{d3|date_timedelta_pprint}}#'
                '{{d4|date_timedelta_pprint}}#'
                '{{d5|date_timedelta_pprint}}'
            )
            render = template.render(Context({
                'd1': (
                    datetime(
                        year=2011, month=3, day=12, hour=20, minute=30, second=21,
                    ) - datetime(
                        year=2011, month=3, day=9,  hour=17, minute=54, second=32,
                    )
                ),
                'd2': (
                    datetime(
                        year=2011, month=3, day=12, hour=20, minute=30, second=21,
                    ) - datetime(
                        year=2011, month=3, day=12, hour=15, minute=54, second=32,
                    )
                ),
                'd3': (
                    datetime(
                        year=2011, month=3, day=12, hour=20, minute=50, second=21,
                    ) - datetime(
                        year=2011, month=3, day=12, hour=20, minute=30, second=32,
                    )
                ),
                'd4': (
                    datetime(
                        year=2011, month=3, day=12, hour=20, minute=50, second=32,
                    ) - datetime(
                        year=2011, month=3, day=12, hour=20, minute=50, second=30,
                    )
                ),
                'd5': (
                    datetime(
                        year=2017, month=9, day=8,  hour=17, minute=6,  second=21,
                    ) - datetime(
                        year=2017, month=9, day=8,  hour=17, minute=6,  second=20,
                    )
                ),
            }))

        self.assertEqual(
            '{}#{}#{}#{}#{}'.format(
                ngettext('{number} day',    '{number} days',     3).format(number=3),
                ngettext('{number} hour',   '{number} hours',    4).format(number=4),
                ngettext('{number} minute', '{number} minutes', 19).format(number=19),
                ngettext('{number} second', '{number} seconds',  2).format(number=2),
                ngettext('{number} second', '{number} seconds',  1).format(number=1),
            ),
            render.strip(),
        )
