# -*- coding: utf-8 -*-

skip_act_tests = False
skip_pattern_tests = False
skip_strategy_tests = False

try:
    from unittest import skipIf

    from creme.creme_core.models import CremePropertyType
    from creme.creme_core.tests.base import CremeTestCase

    from ..models import MarketSegment
    from .. import act_model_is_custom, pattern_model_is_custom, strategy_model_is_custom

    skip_act_tests      = act_model_is_custom()
    skip_pattern_tests  = pattern_model_is_custom()
    skip_strategy_tests = strategy_model_is_custom()
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


def skipIfCustomAct(test_func):
    return skipIf(skip_act_tests, 'Custom Act model in use')(test_func)

def skipIfCustomPattern(test_func):
    return skipIf(skip_pattern_tests, 'Custom ActObjectivePattern model in use')(test_func)

def skipIfCustomStrategy(test_func):
    return skipIf(skip_strategy_tests, 'Custom Strategy model in use')(test_func)


class CommercialBaseTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        CremeTestCase.setUpClass()
        cls.populate('creme_core', 'commercial')

    def setUp(self):
        self.login()

    #def _build_ctypefilter_field(self, ctype, efilter=None):
        #return '{"ctype": "%s", "efilter": "%s"}' % (ctype.id, efilter.id if efilter else '')
    def _build_ctypefilter_field(self, ctype=None, efilter=None):
        return '{"ctype": "%s", "efilter": "%s"}' % (ctype.id if ctype else 0, efilter.id if efilter else '')

    def _create_segment(self):
        #TODO: use a true segment creation view ??
        ptype = CremePropertyType.create('commercial-_prop_unitest', 'Segment type')
        return MarketSegment.objects.create(name='Segment#1', property_type=ptype)
