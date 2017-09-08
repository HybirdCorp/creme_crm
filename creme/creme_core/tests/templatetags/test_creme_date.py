# -*- coding: utf-8 -*-

try:
    from datetime import datetime

    from django.template import Template, Context
    from django.utils.translation import ungettext

    from ..base import CremeTestCase
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


class CremeDateTagsTestCase(CremeTestCase):
    def test_timedelta_pprint(self):
        with self.assertNoException():
            template = Template(r'{% load creme_date %}'
                                '{{d1|timedelta_pprint}}#'
                                '{{d2|timedelta_pprint}}#'
                                '{{d3|timedelta_pprint}}#'
                                '{{d4|timedelta_pprint}}#'
                                '{{d5|timedelta_pprint}}'
                               )
            render = template.render(Context({
                            'd1': datetime(year=2011, month=3, day=12, hour=20, minute=30, second=21) -
                                  datetime(year=2011, month=3, day=9,  hour=17, minute=54, second=32),
                            'd2': datetime(year=2011, month=3, day=12, hour=20, minute=30, second=21) -
                                  datetime(year=2011, month=3, day=12, hour=15, minute=54, second=32),
                            'd3': datetime(year=2011, month=3, day=12, hour=20, minute=50, second=21) -
                                  datetime(year=2011, month=3, day=12, hour=20, minute=30, second=32),
                            'd4': datetime(year=2011, month=3, day=12, hour=20, minute=50, second=32) -
                                  datetime(year=2011, month=3, day=12, hour=20, minute=50, second=30),
                            'd5': datetime(year=2017, month=9, day=8,  hour=17, minute=6,  second=21) -
                                  datetime(year=2017, month=9, day=8,  hour=17, minute=6,  second=20),
                        }))

        self.assertEqual(u'%s#%s#%s#%s#%s' % (
                                ungettext(u'%s day',     u'%s days',     3) % 3,
                                ungettext(u'%s hour',    u'%s hours',    4) % 4,
                                ungettext(u'%s minute)', u'%s minutes', 19) % 19,
                                ungettext(u'%s second',  u'%s seconds',  2) % 2,
                                ungettext(u'%s second',  u'%s seconds',  1) % 1,
                            ),
                         render.strip()
                        )
