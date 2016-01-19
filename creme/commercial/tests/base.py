# -*- coding: utf-8 -*-

skip_act_tests = False
skip_pattern_tests = False
skip_strategy_tests = False

try:
    from unittest import skipIf

    from creme.creme_core.tests.base import CremeTestCase

    from creme.persons import get_contact_model, get_organisation_model

    from creme.activities import get_activity_model

    from creme.opportunities import get_opportunity_model

    from creme import commercial
    from ..models import MarketSegment

    skip_act_tests      = commercial.act_model_is_custom()
    skip_pattern_tests  = commercial.pattern_model_is_custom()
    skip_strategy_tests = commercial.strategy_model_is_custom()

    Act = commercial.get_act_model()
    ActObjectivePattern = commercial.get_pattern_model()
    Strategy = commercial.get_strategy_model()
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


Contact = get_contact_model()
Organisation = get_organisation_model()

Activity = get_activity_model()

Opportunity = get_opportunity_model()


def skipIfCustomAct(test_func):
    return skipIf(skip_act_tests, 'Custom Act model in use')(test_func)


def skipIfCustomPattern(test_func):
    return skipIf(skip_pattern_tests, 'Custom ActObjectivePattern model in use')(test_func)


def skipIfCustomStrategy(test_func):
    return skipIf(skip_strategy_tests, 'Custom Strategy model in use')(test_func)


class CommercialBaseTestCase(CremeTestCase):
    ADD_SEGMENT_URL = '/commercial/market_segment/add'

    @classmethod
    def setUpClass(cls):
        CremeTestCase.setUpClass()
        cls.populate('creme_core', 'commercial')

    def setUp(self):
        self.login()

    def _build_add_segmentdesc_url(self, strategy):
        return '/commercial/strategy/%s/add/segment/' % strategy.id

    def _build_ctypefilter_field(self, ctype=None, efilter=None):
        return '{"ctype": "%s", "efilter": "%s"}' % (ctype.id if ctype else 0, efilter.id if efilter else '')

    def _create_segment(self, name='Segment#1'):
        self.assertNoFormError(self.client.post(self.ADD_SEGMENT_URL, data={'name': name}))

        return self.get_object_or_fail(MarketSegment, name=name)

    def _create_segment_desc(self, strategy, name, product='', place='', price='', promotion=''):
        response = self.client.post(self._build_add_segmentdesc_url(strategy),
                                    data={'name': name,
                                          'product': product,
                                          'place': place,
                                          'price': price,
                                          'promotion': promotion,
                                         }
                                   )
        self.assertNoFormError(response)

        return strategy.segment_info.get(segment__name=name)
