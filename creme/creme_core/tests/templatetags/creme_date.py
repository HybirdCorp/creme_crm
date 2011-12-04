# -*- coding: utf-8 -*-

try:
    from datetime import datetime

    from django.template import Template, Context
    from django.utils.translation import ugettext as _

    from creme_core.tests.base import CremeTestCase
except Exception as e:
    print 'Error:', e


__all__ = ('CremeDateTagsTestCase',)


class CremeDateTagsTestCase(CremeTestCase):
    def test_timedelta_pprint(self):
        try:
            template = Template('{% load creme_date %}'
                                '{{d1|timedelta_pprint}}#'
                                '{{d2|timedelta_pprint}}#'
                                '{{d3|timedelta_pprint}}#'
                                '{{d4|timedelta_pprint}}'
                               )
            render = template.render(Context({
                            'd1': datetime(year=2011, month=3, day=12, hour=20, minute=30, second=21) - \
                                  datetime(year=2011, month=3, day=9,  hour=17, minute=54, second=32),
                            'd2': datetime(year=2011, month=3, day=12, hour=20, minute=30, second=21) - \
                                  datetime(year=2011, month=3, day=12, hour=15, minute=54, second=32),
                            'd3': datetime(year=2011, month=3, day=12, hour=20, minute=50, second=21) - \
                                  datetime(year=2011, month=3, day=12, hour=20, minute=30, second=32),
                            'd4': datetime(year=2011, month=3, day=12, hour=20, minute=50, second=32) - \
                                  datetime(year=2011, month=3, day=12, hour=20, minute=50, second=30),
                        }))
        except Exception as e:
            self.fail(str(e))

        self.assertEqual(_('%s day(s)') % 3 + '#' + \
                          _('%s hour(s)') % 4 + '#' + \
                          _('%s minute(s)') % 19 + '#' + \
                          _('%s second(s)') % 2,
                         render.strip()
                        )
